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
