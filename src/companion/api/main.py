"""Companion REST API — FastAPI application entry point."""
import contextlib
import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from companion.api.auth import get_api_key
from companion.api.telemetry import setup_telemetry
from companion.api.routes import (
    analysis, benchmark, chat, chat_feedback, context, docs, features, feedback,
    graph, ingest, plugins, runtime, search, tour, webhooks,
)
from companion.core.engine.core_engine import CoreEngine
from companion.graph.neo4j_client import Neo4jClient

_REPO_ROOT  = Path(__file__).resolve().parents[3]
_START_TIME = time.time()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    neo4j = Neo4jClient(
        uri=os.environ.get("NEO4J_URI",      "bolt://localhost:7687"),
        user=os.environ.get("NEO4J_USER",    "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "companion-dev"),
    )
    engine = CoreEngine(
        neo4j_client=neo4j,
        plugin_dirs=[
            _REPO_ROOT / "plugins" / "parsers",
            _REPO_ROOT / "plugins" / "extractors",
            _REPO_ROOT / "plugins" / "compression",
        ],
    )
    await engine.start()
    app.state.engine    = engine
    app.state.neo4j     = neo4j
    app.state.ready     = True
    yield
    app.state.ready = False
    await engine.stop()


app = FastAPI(
    title="Companion API",
    description="AI-native code intelligence platform — evolved from Understand-Anything",
    version="0.1.0",
    lifespan=lifespan,
    # Protect Swagger UI in production
    docs_url=None if os.environ.get("COMPANION_API_KEY") else "/docs",
    redoc_url=None if os.environ.get("COMPANION_API_KEY") else "/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],
)

# Setup OpenTelemetry (no-op when OTEL_EXPORTER_OTLP_ENDPOINT not set)
setup_telemetry(app)

# ── Auth dependency applied to all protected routes ───────────────────────────
_auth = Depends(get_api_key)

app.include_router(analysis.router,      prefix="/api/v1/analysis",  tags=["analysis"],      dependencies=[_auth])
app.include_router(ingest.router,        prefix="/api/v1/analysis",  tags=["ingest"],         dependencies=[_auth])
app.include_router(features.router,      prefix="/api/v1/features",  tags=["features"],       dependencies=[_auth])
app.include_router(feedback.router,      prefix="/api/v1/features",  tags=["feedback"],       dependencies=[_auth])
app.include_router(graph.router,         prefix="/api/v1/graph",     tags=["graph"],          dependencies=[_auth])
app.include_router(plugins.router,       prefix="/api/v1/plugins",   tags=["plugins"],        dependencies=[_auth])
app.include_router(chat.router,          prefix="/api/v1/chat",      tags=["chat"],           dependencies=[_auth])
app.include_router(chat_feedback.router, prefix="/api/v1/chat",      tags=["chat"],           dependencies=[_auth])
app.include_router(docs.router,          prefix="/api/v1/docs",      tags=["docs"],           dependencies=[_auth])
app.include_router(search.router,        prefix="/api/v1/search",    tags=["search"],         dependencies=[_auth])
app.include_router(tour.router,          prefix="/api/v1/tour",      tags=["tour"],           dependencies=[_auth])
app.include_router(benchmark.router,     prefix="/api/v1/benchmark", tags=["benchmark"],      dependencies=[_auth])
app.include_router(runtime.router,       prefix="/api/v1/runtime",   tags=["runtime"],        dependencies=[_auth])
app.include_router(context.router,       prefix="/api/v1/context",   tags=["context"],        dependencies=[_auth])
# Webhooks use their own HMAC signature — not protected by API key
app.include_router(webhooks.router,      prefix="/api/v1/webhooks",  tags=["webhooks"])


# ── Public health endpoints ───────────────────────────────────────────────────

@app.get("/health", tags=["observability"])
async def health():
    """Liveness probe — always returns 200 if the process is running."""
    return {"status": "ok", "uptime_seconds": round(time.time() - _START_TIME)}


@app.get("/ready", tags=["observability"])
async def ready(request: Request):
    """
    Readiness probe — returns 200 only when Neo4j is connected and
    plugins are loaded. Use this for Kubernetes readinessProbe.
    """
    if not getattr(request.app.state, "ready", False):
        from fastapi import Response
        return Response(status_code=503, content="Not ready")

    engine = request.app.state.engine
    neo4j_ok = False
    try:
        await engine.neo4j.query("RETURN 1")
        neo4j_ok = True
    except Exception:
        pass

    plugins_loaded = engine.plugin_manager.loaded_count

    status_code = 200 if neo4j_ok else 503
    body = {
        "status":         "ready" if neo4j_ok else "degraded",
        "neo4j":          neo4j_ok,
        "plugins_loaded": plugins_loaded,
        "uptime_seconds": round(time.time() - _START_TIME),
    }

    from fastapi.responses import JSONResponse
    return JSONResponse(content=body, status_code=status_code)
