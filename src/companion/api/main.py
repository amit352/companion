"""FeatureGraph REST API — FastAPI application entry point."""
import contextlib
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from companion.api.routes import analysis, chat, features, feedback, graph, plugins
from companion.core.engine.core_engine import CoreEngine
from companion.graph.neo4j_client import Neo4jClient

_REPO_ROOT = Path(__file__).resolve().parents[2]


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    neo4j = Neo4jClient(
        uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        user=os.environ.get("NEO4J_USER", "neo4j"),
        password=os.environ.get("NEO4J_PASSWORD", "feature-graph-dev"),
    )
    engine = CoreEngine(
        neo4j_client=neo4j,
        plugin_dirs=[
            _REPO_ROOT / "plugins" / "parsers",
            _REPO_ROOT / "plugins" / "extractors",
            _REPO_ROOT / "plugins" / "compression",
            _REPO_ROOT / "plugins",
        ],
    )
    await engine.start()
    app.state.engine = engine
    yield
    await engine.stop()


app = FastAPI(
    title="FeatureGraph API",
    description="AI-native code intelligence platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(features.router, prefix="/api/v1/features", tags=["features"])
app.include_router(feedback.router, prefix="/api/v1/features", tags=["feedback"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])
app.include_router(plugins.router, prefix="/api/v1/plugins", tags=["plugins"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


@app.get("/health")
async def health():
    return {"status": "ok"}
