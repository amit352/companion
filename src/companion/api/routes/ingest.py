"""
Ingest endpoint for Claude Code integration (Option 2).

When /fg-analyze runs as a Claude Code skill, it extracts features using
Claude Code's session (no API key) and POSTs the results here for persistence.
This endpoint deduplicates, persists to Neo4j, and returns the graph summary.
"""
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

from companion.core.deduplication import deduplicate
from companion.core.agents.graph_builder import GraphBuilder

router = APIRouter()


class IngestFeature(BaseModel):
    name: str
    description: str = ""
    domain: str = "unknown"
    confidence: float = 1.0
    source_files: list[str] = []
    tags: list[str] = []


class IngestRelationship(BaseModel):
    source_id: str
    target_id: str
    kind: str = "depends_on"
    weight: float = 1.0


class IngestRequest(BaseModel):
    repo_path: str
    features: list[IngestFeature]
    relationships: list[IngestRelationship] = []


class IngestResponse(BaseModel):
    nodes_created: int
    edges_created: int
    features_after_dedup: int
    repo_path: str


@router.post("/ingest", response_model=IngestResponse)
async def ingest_features(req: IngestRequest, request: Request) -> IngestResponse:
    """
    Receive features extracted by a Claude Code skill and persist them to Neo4j.
    Used by the /fg-analyze slash command — no ANTHROPIC_API_KEY needed on that path.
    """
    engine = request.app.state.engine

    raw = [f.model_dump() for f in req.features]
    deduped = deduplicate(raw)

    relationships_raw = [r.model_dump() for r in req.relationships]

    builder = GraphBuilder(neo4j=engine.neo4j)
    summary = await builder.build(
        {"features": deduped, "relationships": relationships_raw},
        arch_result={},
    )

    return IngestResponse(
        nodes_created=summary["nodes_created"],
        edges_created=summary["edges_created"],
        features_after_dedup=len(deduped),
        repo_path=req.repo_path,
    )
