"""FeatureGraph REST API — FastAPI application entry point."""
import contextlib
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from feature_graph.api.routes import analysis, features, graph, plugins, chat
from feature_graph.core.engine.core_engine import CoreEngine
from feature_graph.graph.neo4j_client import Neo4jClient


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    neo4j = Neo4jClient(
        uri=os.environ["NEO4J_URI"],
        user=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
    )
    engine = CoreEngine(
        neo4j_client=neo4j,
        plugin_dirs=[
            Path("packages/plugins/parsers"),
            Path("packages/plugins/extractors"),
            Path("packages/compression"),
            Path("plugins"),  # user-installed plugins
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
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])
app.include_router(plugins.router, prefix="/api/v1/plugins", tags=["plugins"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


@app.get("/health")
async def health():
    return {"status": "ok"}
