from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/repositories")
async def list_repositories(request: Request):
    """All analyzed repositories — used by the project switcher."""
    engine = request.app.state.engine
    repos  = await engine.neo4j.query(
        "MATCH (r:Repository) RETURN r ORDER BY r.last_analyzed DESC"
    )
    # Enrich with live feature count per repo
    for repo in repos:
        path = repo.get("path", "")
        if path:
            count = await engine.neo4j.query(
                "MATCH (f:Feature) WHERE any(sf IN f.source_files WHERE sf STARTS WITH $p OR $full STARTS WITH sf) RETURN count(f) AS n",
                p=path.rstrip("/") + "/",
                full=path,
            )
            repo["live_feature_count"] = count[0]["n"] if count else repo.get("feature_count", 0)
    return {"repositories": repos}


@router.get("/overview")
async def graph_overview(request: Request, repo_path: str | None = Query(None)):
    engine = request.app.state.engine
    if repo_path:
        counts = await engine.neo4j.query("""
            MATCH (f:Feature)
            WHERE any(sf IN f.source_files WHERE sf STARTS WITH $p)
            RETURN 'Feature' AS label, count(f) AS count
        """, p=repo_path.rstrip("/") + "/")
    else:
        counts = await engine.neo4j.query(
            "MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC"
        )
    edge_counts = await engine.neo4j.query(
        "MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count ORDER BY count DESC"
    )
    return {"nodes": counts, "edges": edge_counts}


@router.get("/compressed-context")
async def compressed_context(request: Request, q: str | None = None, repo_path: str | None = None):
    from companion.graph.compressor import compress
    engine   = request.app.state.engine
    features = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 200")
    rels     = await engine.neo4j.query(
        "MATCH (a)-[r]->(b) RETURN a.id AS source_id, b.id AS target_id, type(r) AS kind LIMIT 500"
    )
    return compress(features, rels, query=q)


@router.get("/relationships")
async def get_relationships(request: Request, repo_path: str | None = Query(None)):
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
    engine  = request.app.state.engine
    results = await engine.neo4j.query(
        "MATCH (n) WHERE toLower(n.name) CONTAINS toLower($q) RETURN n, labels(n) as labels LIMIT 20",
        q=q,
    )
    return {"results": results}
