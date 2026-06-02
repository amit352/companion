"""
Ingest endpoint — accepts all 6 SRS node types:
  Feature, Service, API, DatabaseTable, UIComponent, Requirement
plus relationships between any of them.

Every ingest is recorded in Postgres (analysis_runs) and creates/updates
a Repository node in Neo4j linking to all ingested nodes.
"""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

from companion.core.deduplication import deduplicate
from companion.core.agents.graph_builder import GraphBuilder
from companion.graph.models.nodes import (
    API, DatabaseTable, Feature, Requirement, Service, UIComponent,
)
from companion.graph.models.relationships import GraphRelationship

log = structlog.get_logger()
router = APIRouter()


# ── Request models (one per SRS node type) ───────────────────────────────────

class IngestFeature(BaseModel):
    name: str
    description: str = ""
    domain: str = "unknown"
    confidence: float = 1.0
    source_files: list[str] = []
    tags: list[str] = []

class IngestService(BaseModel):
    name: str
    technology: str = ""
    source_files: list[str] = []
    tags: list[str] = []

class IngestAPI(BaseModel):
    path: str
    method: str = "GET"
    service_name: str = ""
    source_files: list[str] = []
    auth_required: bool = True

class IngestDatabaseTable(BaseModel):
    name: str
    database: str = ""
    engine: str = "postgresql"
    source_files: list[str] = []

class IngestUIComponent(BaseModel):
    name: str
    path: str = ""
    framework: str = "react"
    source_files: list[str] = []

class IngestRequirement(BaseModel):
    title: str
    description: str = ""
    source: str = ""        # e.g. "JIRA-123"
    priority: str = "medium"

class IngestRelationship(BaseModel):
    source_id: str          # node name or id
    target_id: str
    kind: str = "depends_on"
    weight: float = 1.0

class IngestRequest(BaseModel):
    repo_path: str
    repo_name: str = ""
    trigger: str = "manual"
    # Node payloads
    features:        list[IngestFeature]       = []
    services:        list[IngestService]       = []
    apis:            list[IngestAPI]           = []
    database_tables: list[IngestDatabaseTable] = []
    ui_components:   list[IngestUIComponent]   = []
    requirements:    list[IngestRequirement]   = []
    relationships:   list[IngestRelationship]  = []

class IngestResponse(BaseModel):
    run_id: str
    nodes_created: int
    edges_created: int
    features_after_dedup: int
    repo_path: str
    repo_name: str
    node_breakdown: dict[str, int]


# ── Postgres run recorder ─────────────────────────────────────────────────────

def _record_run(repo_path, repo_name, trigger, features_in, nodes_created, edges_created) -> str:
    run_id = ""
    try:
        import psycopg2
        dsn = os.environ.get("POSTGRES_DSN", "postgresql://companion:companion-dev@localhost:5433/companion")
        conn = psycopg2.connect(dsn)
        cur  = conn.cursor()
        cur.execute(
            """INSERT INTO analysis_runs
                 (repo_path, repo_name, trigger, features_in, features_out, edges_out, status)
               VALUES (%s, %s, %s, %s, %s, %s, 'completed') RETURNING id""",
            (repo_path, repo_name or Path(repo_path).name, trigger,
             features_in, nodes_created, edges_created),
        )
        run_id = str(cur.fetchone()[0])
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        log.warning("run_record_failed", error=str(e))
    return run_id


async def _upsert_repository(neo4j, repo_path: str, repo_name: str, feature_count: int) -> None:
    name = repo_name or Path(repo_path).name
    await neo4j.query(
        "MERGE (r:Repository {path: $path}) SET r.name=$name, r.last_analyzed=$ts, r.feature_count=$count",
        path=repo_path, name=name,
        ts=datetime.now(timezone.utc).isoformat(), count=feature_count,
    )


# ── Name → ID resolution (relationships use names, not UUIDs from agent output) ──

def _build_name_map(created: list[tuple[str, Any]]) -> dict[str, str]:
    """Map node name → Neo4j id for relationship resolution."""
    m: dict[str, str] = {}
    for _, node in created:
        name = getattr(node, "name", None) or getattr(node, "path", None) or getattr(node, "title", None)
        if name:
            m[name] = node.id
    return m


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def ingest_features(req: IngestRequest, request: Request) -> IngestResponse:
    engine = request.app.state.engine
    neo4j  = engine.neo4j

    breakdown: dict[str, int] = {}
    created: list[tuple[str, Any]] = []   # (label, node)

    # ── Features (with deduplication) ───────────────────
    raw_feats = [f.model_dump() for f in req.features]
    deduped   = deduplicate(raw_feats)
    # Stamp repo_path on every feature so per-project filtering works
    for feat in deduped:
        feat["repo_path"] = req.repo_path
    builder   = GraphBuilder(neo4j=neo4j)
    feat_summary = await builder.build({"features": deduped, "relationships": []}, arch_result={})
    breakdown["Feature"] = feat_summary["nodes_created"]

    # Rebuild feat name→id map from Neo4j (builder created them)
    feat_rows = await neo4j.query(
        "MATCH (f:Feature) WHERE f.name IN $names RETURN f.id as id, f.name as name",
        names=[f["name"] for f in deduped],
    )
    name_to_id: dict[str, str] = {r["name"]: r["id"] for r in feat_rows}

    # ── Services ─────────────────────────────────────────
    for s in req.services:
        node = Service(name=s.name, technology=s.technology)
        await neo4j.upsert_node(node)
        name_to_id[s.name] = node.id
        created.append(("Service", node))
    breakdown["Service"] = len(req.services)

    # ── APIs ──────────────────────────────────────────────
    for a in req.apis:
        # Find service id if referenced by name
        svc_id = name_to_id.get(a.service_name, "")
        node = API(path=a.path, method=a.method.upper(), service_id=svc_id,
                   auth_required=a.auth_required)
        await neo4j.upsert_node(node)
        name_to_id[a.path] = node.id
        created.append(("API", node))
    breakdown["API"] = len(req.apis)

    # ── DatabaseTables ────────────────────────────────────
    for t in req.database_tables:
        node = DatabaseTable(name=t.name, database=t.database, engine=t.engine)
        await neo4j.upsert_node(node)
        name_to_id[t.name] = node.id
        created.append(("DatabaseTable", node))
    breakdown["DatabaseTable"] = len(req.database_tables)

    # ── UIComponents ──────────────────────────────────────
    for u in req.ui_components:
        node = UIComponent(name=u.name, path=u.path, framework=u.framework)
        await neo4j.upsert_node(node)
        name_to_id[u.name] = node.id
        created.append(("UIComponent", node))
    breakdown["UIComponent"] = len(req.ui_components)

    # ── Requirements ─────────────────────────────────────
    for r in req.requirements:
        node = Requirement(title=r.title, description=r.description,
                           source=r.source, priority=r.priority)
        await neo4j.upsert_node(node)
        name_to_id[r.title] = node.id
        created.append(("Requirement", node))
    breakdown["Requirement"] = len(req.requirements)

    # ── Relationships ─────────────────────────────────────
    edges_created = feat_summary["edges_created"]
    for rel in req.relationships:
        src_id = name_to_id.get(rel.source_id) or rel.source_id
        tgt_id = name_to_id.get(rel.target_id) or rel.target_id
        if src_id and tgt_id and src_id != tgt_id:
            kind = rel.kind.upper().replace(" ", "_").replace("-", "_")
            r_node = GraphRelationship(source_id=src_id, target_id=tgt_id,
                                       rel_type=kind, weight=rel.weight)
            try:
                await neo4j.upsert_relationship(r_node)
                edges_created += 1
            except Exception as e:
                log.debug("rel_skipped", src=rel.source_id, tgt=rel.target_id, error=str(e))

    nodes_created = sum(breakdown.values())
    await _upsert_repository(neo4j, req.repo_path, req.repo_name, breakdown.get("Feature", 0))

    run_id = _record_run(req.repo_path, req.repo_name, req.trigger,
                         len(req.features), nodes_created, edges_created)

    log.info("ingest_complete", repo=req.repo_path,
             nodes=nodes_created, edges=edges_created,
             breakdown=breakdown, run_id=run_id)

    return IngestResponse(
        run_id=run_id,
        nodes_created=nodes_created,
        edges_created=edges_created,
        features_after_dedup=len(deduped),
        repo_path=req.repo_path,
        repo_name=req.repo_name or Path(req.repo_path).name,
        node_breakdown=breakdown,
    )


@router.get("/runs")
async def list_runs(limit: int = 20):
    try:
        import psycopg2
        dsn = os.environ.get("POSTGRES_DSN", "postgresql://companion:companion-dev@localhost:5433/companion")
        conn = psycopg2.connect(dsn)
        cur  = conn.cursor()
        cur.execute(
            """SELECT id, repo_name, repo_path, trigger, features_out, edges_out,
                      status, completed_at
               FROM analysis_runs ORDER BY completed_at DESC LIMIT %s""",
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        for row in rows:
            if row.get("completed_at"):
                row["completed_at"] = row["completed_at"].isoformat()
        cur.close(); conn.close()
        return {"runs": rows}
    except Exception as e:
        return {"runs": [], "error": str(e)}
