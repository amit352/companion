from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/overview")
async def graph_overview(request: Request):
    """Return node/edge counts by type for the dashboard summary."""
    engine = request.app.state.engine
    counts = await engine.neo4j.query("""
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
    """)
    edge_counts = await engine.neo4j.query("""
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(r) as count
        ORDER BY count DESC
    """)
    return {"nodes": counts, "edges": edge_counts}


@router.get("/compressed-context")
async def compressed_context(request: Request, q: str | None = None):
    """Phase 3 — deterministic graph compression for AI context."""
    from companion.graph.compressor import compress
    engine = request.app.state.engine
    features = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 200")
    rels = await engine.neo4j.query(
        "MATCH (a)-[r]->(b) RETURN a.id AS source_id, b.id AS target_id, type(r) AS kind LIMIT 500"
    )
    return compress(features, rels, query=q)


@router.get("/relationships")
async def get_relationships(request: Request):
    """Return all graph relationships as source_id, target_id, kind."""
    engine = request.app.state.engine
    records = await engine.neo4j.query("""
        MATCH (a)-[r]->(b)
        RETURN a.id AS source_id, b.id AS target_id,
               type(r) AS kind, r.weight AS weight
        LIMIT 500
    """)
    return {"relationships": records}


@router.get("/search")
async def search_graph(q: str, request: Request):
    """Full-text search across all node names (FR-9)."""
    engine = request.app.state.engine
    results = await engine.neo4j.query(
        """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($q)
        RETURN n, labels(n) as labels
        LIMIT 20
        """,
        q=q,
    )
    return {"results": results}
