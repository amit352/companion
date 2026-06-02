"""
Runtime analysis endpoints (SRS 4.5).

POST /api/v1/runtime/traces   — receive OTel spans, run analysis, persist to graph
GET  /api/v1/runtime/graph    — fetch runtime dependency graph
GET  /api/v1/runtime/bottlenecks — fetch bottleneck analysis

Span format (simplified OTLP-compatible):
  {
    "trace_id": "abc123",
    "span_id":  "def456",
    "operation": "GET /api/v1/invoices",
    "service":   "scicustomer-api",
    "duration_ms": 142.5,
    "status":    "ok",
    "tags": { "http.route": "/api/v1/invoices", "db.name": "companion" }
  }
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class SpanInput(BaseModel):
    trace_id:    str
    span_id:     str
    operation:   str
    service:     str
    duration_ms: float
    status:      str = "ok"
    tags:        dict = {}


class TracesRequest(BaseModel):
    spans: list[SpanInput]


@router.post("/traces")
async def ingest_traces(req: TracesRequest, request: Request):
    """Receive trace spans, analyze, and persist runtime relationships to Neo4j."""
    from companion.sdk.base.runtime_plugin import TraceSpan
    from companion.sdk.base.plugin_base import PluginType

    engine  = request.app.state.engine
    spans   = [
        TraceSpan(
            trace_id=s.trace_id, span_id=s.span_id,
            operation=s.operation, service=s.service,
            duration_ms=s.duration_ms, status=s.status, tags=s.tags,
        )
        for s in req.spans
    ]

    # Find the OTel runtime plugin
    analyzers = engine.registry.get_by_type(PluginType.RUNTIME_ANALYSIS)
    if not analyzers:
        # Load on demand if not registered
        import importlib.util, json
        from pathlib import Path
        from companion.sdk.base.plugin_base import PluginManifest
        mp = Path("plugins/runtime/otel_plugin/plugin.json")
        if mp.exists():
            data = json.loads(mp.read_text())
            spec = importlib.util.spec_from_file_location("otel_plugin", mp.parent / "plugin.py")
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            analyzer = mod.Plugin(PluginManifest(**data))
        else:
            return {"error": "OTel runtime plugin not found", "spans_received": len(spans)}
    else:
        analyzer = analyzers[0]

    result = await analyzer.analyze_traces(spans)

    # Persist runtime edges to Neo4j
    edges_created = 0
    for edge in result.edges:
        try:
            await engine.neo4j.query(
                """
                MERGE (a:Service {name: $src})
                MERGE (b:Service {name: $tgt})
                MERGE (a)-[r:CALLS_IN_RUNTIME]->(b)
                SET r.frequency = coalesce(r.frequency, 0) + $freq
                """,
                src=edge["source"], tgt=edge["target"], freq=edge.get("frequency", 1),
            )
            edges_created += 1
        except Exception:
            pass

    return {
        "spans_received":  len(spans),
        "services_found":  len(result.nodes),
        "edges_created":   edges_created,
        "bottlenecks":     len(result.bottlenecks),
        "analysis":        result.model_dump(),
    }


@router.get("/graph")
async def runtime_graph(request: Request):
    """Return the runtime service dependency graph from trace data."""
    engine = request.app.state.engine
    nodes  = await engine.neo4j.query(
        "MATCH (s:Service) RETURN s.name AS name, s.avg_duration_ms AS avg_ms, s.call_count AS calls"
    )
    edges  = await engine.neo4j.query(
        "MATCH (a:Service)-[r:CALLS_IN_RUNTIME]->(b:Service) "
        "RETURN a.name AS source, b.name AS target, r.frequency AS frequency "
        "ORDER BY frequency DESC LIMIT 100"
    )
    return {"nodes": nodes, "edges": edges}


@router.get("/bottlenecks")
async def bottlenecks(request: Request):
    """Return services with above-average response times."""
    engine = request.app.state.engine
    result = await engine.neo4j.query(
        """
        MATCH (s:Service)
        WHERE s.avg_duration_ms IS NOT NULL
        RETURN s.name AS service, s.avg_duration_ms AS avg_ms, s.call_count AS calls
        ORDER BY avg_ms DESC LIMIT 20
        """
    )
    return {"bottlenecks": result}
