"""
Guided codebase tour — ordered walkthrough of key features.

Algorithm:
  1. Start from features with no incoming dependencies (root nodes)
  2. BFS following DEPENDS_ON edges
  3. Within each BFS level, sort by confidence desc
  4. Cap at 10 steps — keep the tour focused

This mirrors Understand-Anything's guided tour concept but uses the
actual dependency graph to determine meaningful ordering.
"""
from collections import defaultdict, deque
from typing import Any

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def get_tour(request: Request) -> dict[str, Any]:
    engine    = request.app.state.engine
    features  = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 200")
    rels      = await engine.neo4j.query(
        "MATCH (a)-[r:DEPENDS_ON]->(b) RETURN a.id AS src, b.id AS tgt LIMIT 500"
    )

    if not features:
        return {"steps": [], "total": 0}

    by_id = {f["id"]: f for f in features}

    # Build adjacency: who depends on X (in-edges)
    in_edges: dict[str, list[str]] = defaultdict(list)   # id → list of ids that point TO id
    out_edges: dict[str, list[str]] = defaultdict(list)  # id → list of ids it points TO

    for r in rels:
        out_edges[r["src"]].append(r["tgt"])
        in_edges[r["tgt"]].append(r["src"])

    # Root nodes = no one depends on them (low in-degree = foundational)
    roots = [
        fid for fid in by_id
        if len(in_edges.get(fid, [])) == 0
    ]

    # Sort roots by out-degree desc (most connected foundations first)
    roots.sort(key=lambda fid: -len(out_edges.get(fid, [])))

    # BFS to generate ordered tour
    visited: list[str] = []
    seen: set[str]     = set()
    queue              = deque(roots)

    while queue and len(visited) < 12:
        fid = queue.popleft()
        if fid in seen or fid not in by_id:
            continue
        seen.add(fid)
        visited.append(fid)
        # Enqueue dependencies sorted by confidence
        deps = sorted(
            out_edges.get(fid, []),
            key=lambda d: -by_id.get(d, {}).get("confidence", 0),
        )
        queue.extend(deps)

    # Fallback: add any unvisited features sorted by confidence
    remaining = sorted(
        [fid for fid in by_id if fid not in seen],
        key=lambda fid: -by_id[fid].get("confidence", 0),
    )
    visited.extend(remaining[:max(0, 10 - len(visited))])
    visited = visited[:10]

    steps = [
        {
            "step":        i + 1,
            "total":       len(visited),
            "id":          fid,
            "name":        by_id[fid]["name"],
            "description": by_id[fid].get("description", ""),
            "domain":      by_id[fid].get("domain", ""),
            "confidence":  by_id[fid].get("confidence", 1.0),
            "tags":        by_id[fid].get("tags", []),
            "depends_on":  [
                by_id[d]["name"] for d in out_edges.get(fid, []) if d in by_id
            ][:3],
        }
        for i, fid in enumerate(visited)
    ]

    return {"steps": steps, "total": len(steps)}
