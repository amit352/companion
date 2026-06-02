"""
Ingest endpoint for Claude Code integration.

When /companion or /fg-analyze runs, it extracts features using the Claude Code
session and POSTs results here for persistence. Every ingest is recorded in
Postgres (analysis_runs) and in Neo4j as a Repository node so the full history
is queryable.
"""
import os
from datetime import datetime, timezone
from pathlib import Path

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

from companion.core.deduplication import deduplicate
from companion.core.agents.graph_builder import GraphBuilder

log = structlog.get_logger()
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
    repo_name: str = ""          # optional display name, e.g. "Understand-Anything"
    trigger: str = "manual"      # manual | webhook | scheduled
    features: list[IngestFeature]
    relationships: list[IngestRelationship] = []


class IngestResponse(BaseModel):
    run_id: str
    nodes_created: int
    edges_created: int
    features_after_dedup: int
    repo_path: str
    repo_name: str


# ── Postgres run recorder ─────────────────────────────────────────────────────

def _record_run(
    repo_path: str,
    repo_name: str,
    trigger: str,
    features_in: int,
    nodes_created: int,
    edges_created: int,
) -> str:
    run_id = ""
    try:
        import psycopg2
        dsn = os.environ.get("POSTGRES_DSN", "postgresql://companion:companion-dev@localhost:5433/companion")
        conn = psycopg2.connect(dsn)
        cur  = conn.cursor()
        cur.execute(
            """
            INSERT INTO analysis_runs
              (repo_path, repo_name, trigger, features_in, features_out, edges_out, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'completed')
            RETURNING id
            """,
            (repo_path, repo_name or Path(repo_path).name, trigger,
             features_in, nodes_created, edges_created),
        )
        run_id = str(cur.fetchone()[0])
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        log.warning("run_record_failed", error=str(e))
    return run_id


# ── Neo4j Repository node ─────────────────────────────────────────────────────

async def _upsert_repository(neo4j, repo_path: str, repo_name: str, feature_count: int) -> None:
    """Create or update a Repository node so repos are queryable in the graph."""
    name = repo_name or Path(repo_path).name
    await neo4j.query(
        """
        MERGE (r:Repository {path: $path})
        SET r.name = $name,
            r.last_analyzed = $ts,
            r.feature_count = $count
        """,
        path=repo_path,
        name=name,
        ts=datetime.now(timezone.utc).isoformat(),
        count=feature_count,
    )
    # Schema constraint (idempotent)
    try:
        await neo4j.query(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repository) REQUIRE r.path IS UNIQUE"
        )
    except Exception:
        pass


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
async def ingest_features(req: IngestRequest, request: Request) -> IngestResponse:
    engine = request.app.state.engine

    raw    = [f.model_dump() for f in req.features]
    deduped = deduplicate(raw)
    rels    = [r.model_dump() for r in req.relationships]

    builder = GraphBuilder(neo4j=engine.neo4j)
    summary = await builder.build({"features": deduped, "relationships": rels}, arch_result={})

    # Persist Repository node to Neo4j
    await _upsert_repository(
        engine.neo4j, req.repo_path, req.repo_name, summary["nodes_created"]
    )

    # Record run in Postgres
    run_id = _record_run(
        repo_path=req.repo_path,
        repo_name=req.repo_name,
        trigger=req.trigger,
        features_in=len(raw),
        nodes_created=summary["nodes_created"],
        edges_created=summary["edges_created"],
    )

    log.info(
        "ingest_complete",
        repo=req.repo_path,
        features_in=len(raw),
        nodes=summary["nodes_created"],
        edges=summary["edges_created"],
        run_id=run_id,
    )

    return IngestResponse(
        run_id=run_id,
        nodes_created=summary["nodes_created"],
        edges_created=summary["edges_created"],
        features_after_dedup=len(deduped),
        repo_path=req.repo_path,
        repo_name=req.repo_name or Path(req.repo_path).name,
    )


@router.get("/runs")
async def list_runs(limit: int = 20):
    """Return recent analysis run history from Postgres."""
    try:
        import psycopg2
        dsn = os.environ.get("POSTGRES_DSN", "postgresql://companion:companion-dev@localhost:5433/companion")
        conn = psycopg2.connect(dsn)
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT id, repo_name, repo_path, trigger, features_out, edges_out,
                   status, completed_at
            FROM analysis_runs
            ORDER BY completed_at DESC
            LIMIT %s
            """,
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
