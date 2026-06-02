from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/")
async def list_features(
    request: Request,
    domain: str | None = Query(None),
    limit: int = Query(50, le=500),
):
    engine = request.app.state.engine
    cypher = "MATCH (f:Feature) RETURN f LIMIT $limit"
    params = {"limit": limit}
    if domain:
        cypher = "MATCH (f:Feature {domain: $domain}) RETURN f LIMIT $limit"
        params["domain"] = domain
    records = await engine.neo4j.query(cypher, **params)
    return {"features": records}


@router.get("/{feature_id}")
async def get_feature(feature_id: str, request: Request):
    engine = request.app.state.engine
    records = await engine.neo4j.query(
        "MATCH (f:Feature {id: $id}) RETURN f", id=feature_id
    )
    if not records:
        raise HTTPException(status_code=404, detail="Feature not found")
    return records[0]


@router.get("/{feature_id}/subgraph")
async def get_feature_subgraph(feature_id: str, depth: int = Query(2, le=5), request: Request = None):
    engine = request.app.state.engine
    return await engine.neo4j.get_feature_subgraph(feature_id, depth=depth)


@router.get("/{feature_id}/impact")
async def get_impact_analysis(feature_id: str, request: Request):
    """What breaks if this feature changes? (FR-4)"""
    engine = request.app.state.engine
    return {"dependents": await engine.neo4j.impact_analysis(feature_id)}
