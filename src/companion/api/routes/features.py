from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/")
async def list_features(
    request: Request,
    domain:    str | None = Query(None),
    repo_path: str | None = Query(None, description="Filter by repository path"),
    limit:     int        = Query(200, le=500),
):
    engine = request.app.state.engine
    if repo_path:
        cypher = """
        MATCH (r:Repository {path: $repo})<-[:CONTAINS]-(f:Feature)
        RETURN f LIMIT $limit
        """
        # Fallback: repo may not have CONTAINS edges yet — match by source_files prefix
        records = await engine.neo4j.query(cypher, repo=repo_path, limit=limit)
        if not records:
            cypher = """
            MATCH (f:Feature)
            WHERE any(sf IN f.source_files WHERE sf STARTS WITH $prefix OR $prefix ENDS WITH '/')
            RETURN f LIMIT $limit
            """
            records = await engine.neo4j.query(cypher, prefix=repo_path.rstrip("/"), limit=limit)
    elif domain:
        records = await engine.neo4j.query(
            "MATCH (f:Feature {domain: $domain}) RETURN f LIMIT $limit",
            domain=domain, limit=limit,
        )
    else:
        records = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT $limit", limit=limit)
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


@router.get("/{feature_id}/full")
async def get_feature_full(feature_id: str, request: Request):
    """
    Full feature detail for the UI panel — includes:
    - Feature data
    - Dependencies (what it needs)
    - Dependents / impact (what needs it), with levels
    - Related nodes: APIs, Services, DB tables
    - Context text for Claude injection
    """
    engine = request.app.state.engine

    # Core feature
    records = await engine.neo4j.query("MATCH (f:Feature {id: $id}) RETURN f", id=feature_id)
    if not records:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Feature not found")
    feature = records[0]

    # What this feature DEPENDS ON (outgoing edges)
    dependencies = await engine.neo4j.query(
        """
        MATCH (f:Feature {id: $id})-[:DEPENDS_ON]->(dep)
        RETURN dep.id AS id, dep.name AS name, labels(dep)[0] AS type,
               dep.domain AS domain, dep.description AS description
        """,
        id=feature_id,
    )

    # What DEPENDS ON this feature — level 1 (direct) and level 2
    direct_dependents = await engine.neo4j.query(
        """
        MATCH (dep)-[:DEPENDS_ON]->(f:Feature {id: $id})
        RETURN DISTINCT dep.id AS id, dep.name AS name, labels(dep)[0] AS type,
               dep.domain AS domain, dep.description AS description
        """,
        id=feature_id,
    )

    # Level 2 dependents (what depends on the dependents)
    direct_ids = [d["id"] for d in direct_dependents]
    level2_dependents = []
    if direct_ids:
        level2_dependents = await engine.neo4j.query(
            """
            MATCH (dep2)-[:DEPENDS_ON]->(dep1)-[:DEPENDS_ON]->(f:Feature {id: $id})
            WHERE NOT dep2.id IN $direct_ids AND dep2.id <> $id
            RETURN DISTINCT dep2.id AS id, dep2.name AS name, labels(dep2)[0] AS type,
                   dep2.domain AS domain
            LIMIT 10
            """,
            id=feature_id,
            direct_ids=direct_ids,
        )

    # Related non-Feature nodes (APIs, Services, DB tables)
    related = await engine.neo4j.query(
        """
        MATCH (f:Feature {id: $id})-[r]-(other)
        WHERE NOT other:Feature AND NOT other:Repository
        RETURN DISTINCT other.id AS id,
               coalesce(other.name, other.path, other.title) AS name,
               labels(other)[0] AS type,
               type(r) AS relationship
        LIMIT 20
        """,
        id=feature_id,
    )

    # Compact context text for Claude
    context_lines = [
        f"Feature: {feature.get('name')} [{feature.get('domain')}]",
        f"Description: {feature.get('description', '')}",
        f"Source: {', '.join(feature.get('source_files', [])[:3])}",
        f"Confidence: {int(feature.get('confidence', 1.0) * 100)}%",
    ]
    if dependencies:
        context_lines.append(f"Depends on: {', '.join(d['name'] for d in dependencies)}")
    if direct_dependents:
        context_lines.append(f"Used by: {', '.join(d['name'] for d in direct_dependents[:5])}")
    if related:
        for r in related[:5]:
            context_lines.append(f"{r['relationship']}: {r['name']} ({r['type']})")

    return {
        "feature":           feature,
        "dependencies":      dependencies,       # what it needs
        "direct_dependents": direct_dependents,  # level 1 blast radius
        "level2_dependents": level2_dependents,  # level 2 blast radius
        "related_nodes":     related,            # APIs, Services, DB tables
        "blast_radius":      len(direct_dependents) + len(level2_dependents),
        "context_for_claude": "\n".join(context_lines),
    }
