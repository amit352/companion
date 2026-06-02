"""
Phase 3 — Deterministic graph compression.

Converts the Neo4j feature graph into a compact, token-efficient context
that can be passed to an LLM or used for graph-native Q&A.

No API calls needed — pure graph traversal + heuristics.
Target: 27 features → ~800 tokens (vs ~8,000 raw).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def compress(
    features: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    query: str | None = None,
) -> dict[str, Any]:
    """
    Build a compressed context from graph data.
    If query is provided, biases compression toward relevant features.
    """
    if not features:
        return _empty()

    # --- Build lookup structures ---
    feat_by_id = {f["id"]: f for f in features}
    feat_by_name = {f["name"]: f for f in features}

    # In-degree and out-degree per node
    in_deg: dict[str, int] = defaultdict(int)
    out_deg: dict[str, int] = defaultdict(int)
    dependents: dict[str, list[str]] = defaultdict(list)   # who depends on X
    dependencies: dict[str, list[str]] = defaultdict(list)  # what X depends on

    for r in relationships:
        src, tgt = r.get("source_id"), r.get("target_id")
        if src and tgt:
            out_deg[src] += 1
            in_deg[tgt] += 1
            dependents[tgt].append(src)
            dependencies[src].append(tgt)

    # --- Importance score: high in-degree = high blast radius ---
    def importance(f: dict[str, Any]) -> float:
        fid = f["id"]
        return (
            in_deg[fid] * 2.0        # dependents weight most
            + out_deg[fid] * 0.5
            + f.get("confidence", 0.8)
        )

    ranked = sorted(features, key=importance, reverse=True)

    # --- Query-biased re-ranking ---
    if query:
        q_lower = query.lower()
        def query_score(f: dict[str, Any]) -> float:
            name_match = sum(1 for w in q_lower.split() if w in f["name"].lower())
            desc_match = sum(1 for w in q_lower.split() if w in f.get("description", "").lower())
            return importance(f) + name_match * 3 + desc_match
        ranked = sorted(features, key=query_score, reverse=True)

    # --- Domain clusters ---
    by_domain: dict[str, list[str]] = defaultdict(list)
    for f in features:
        by_domain[f.get("domain", "unknown")].append(f["name"])

    # --- Feature summaries (top 20 by importance) ---
    summaries = []
    for f in ranked[:20]:
        fid = f["id"]
        dep_names = [feat_by_id[d]["name"] for d in dependencies[fid] if d in feat_by_id]
        dependent_names = [feat_by_id[d]["name"] for d in dependents[fid] if d in feat_by_id]
        summaries.append({
            "name": f["name"],
            "domain": f.get("domain", "unknown"),
            "description": f.get("description", ""),
            "confidence": round(f.get("confidence", 1.0), 2),
            "depends_on": dep_names[:5],
            "depended_on_by": dependent_names[:5],
            "source_files": f.get("source_files", [])[:3],
            "importance_rank": ranked.index(f) + 1,
        })

    # --- Compact relationship list ---
    rel_list = [
        {
            "from": feat_by_id.get(r["source_id"], {}).get("name", r["source_id"]),
            "to":   feat_by_id.get(r["target_id"], {}).get("name", r["target_id"]),
        }
        for r in relationships
        if r.get("source_id") in feat_by_id and r.get("target_id") in feat_by_id
    ]

    raw_tokens = sum(
        len(f.get("description", "").split()) + len(f.get("name", "").split())
        for f in features
    ) * 2
    compressed_tokens = sum(
        len(s["description"].split()) + len(s["name"].split()) + 4
        for s in summaries
    )

    return {
        "domain_clusters": {d: names for d, names in sorted(by_domain.items())},
        "feature_summaries": summaries,
        "relationships": rel_list,
        "stats": {
            "total_features": len(features),
            "total_relationships": len(relationships),
            "shown_features": len(summaries),
            "raw_token_estimate": raw_tokens,
            "compressed_token_estimate": compressed_tokens,
            "compression_ratio": round(1 - compressed_tokens / max(raw_tokens, 1), 2),
        },
    }


def _empty() -> dict[str, Any]:
    return {
        "domain_clusters": {},
        "feature_summaries": [],
        "relationships": [],
        "stats": {
            "total_features": 0, "total_relationships": 0,
            "shown_features": 0, "raw_token_estimate": 0,
            "compressed_token_estimate": 0, "compression_ratio": 0,
        },
    }


def impact_context(
    feature_name: str,
    features: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build focused context for 'what breaks if X changes?' questions.
    Returns direct and transitive dependents, sorted by depth.
    """
    feat_by_id = {f["id"]: f for f in features}
    feat_by_name_lower = {f["name"].lower(): f for f in features}

    target = feat_by_name_lower.get(feature_name.lower())
    if not target:
        return {"error": f"Feature '{feature_name}' not found", "dependents": []}

    # BFS upward through dependency graph
    dependents_map: dict[str, list[str]] = defaultdict(list)
    for r in relationships:
        src, tgt = r.get("source_id"), r.get("target_id")
        if src and tgt:
            dependents_map[tgt].append(src)

    visited: dict[str, int] = {}
    queue = [(target["id"], 0)]
    while queue:
        fid, depth = queue.pop(0)
        if fid in visited:
            continue
        visited[fid] = depth
        for dep_id in dependents_map.get(fid, []):
            if dep_id not in visited:
                queue.append((dep_id, depth + 1))

    dependents = [
        {
            "name": feat_by_id[fid]["name"],
            "domain": feat_by_id[fid].get("domain"),
            "depth": d,
            "description": feat_by_id[fid].get("description", ""),
        }
        for fid, d in sorted(visited.items(), key=lambda x: x[1])
        if fid != target["id"] and fid in feat_by_id
    ]

    return {
        "feature": target["name"],
        "description": target.get("description", ""),
        "direct_dependents": [x for x in dependents if x["depth"] == 1],
        "transitive_dependents": [x for x in dependents if x["depth"] > 1],
        "total_blast_radius": len(dependents),
    }
