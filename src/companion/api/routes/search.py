"""
Semantic search using BM25 ranking over feature names, descriptions, and tags.
No API key or model download needed — pure TF-IDF based relevance.
Better than substring: 'invoice payment' matches 'Invoice Fee Calculation'.
"""
from typing import Any

from fastapi import APIRouter, Request
from rank_bm25 import BM25Okapi

router = APIRouter()


def _tokenize(text: str) -> list[str]:
    return text.lower().replace("-", " ").replace("_", " ").split()


def _build_corpus(features: list[dict[str, Any]]) -> list[list[str]]:
    docs = []
    for f in features:
        tokens = (
            _tokenize(f.get("name", ""))
            + _tokenize(f.get("description", ""))
            + [t.lower() for t in f.get("tags", [])]
            + [f.get("domain", "")]
        )
        docs.append(tokens)
    return docs


@router.get("/semantic")
async def semantic_search(q: str, request: Request, limit: int = 8) -> dict[str, Any]:
    if not q.strip():
        return {"results": [], "query": q}

    engine   = request.app.state.engine
    features = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 500")

    if not features:
        return {"results": [], "query": q}

    corpus  = _build_corpus(features)
    bm25    = BM25Okapi(corpus)
    scores  = bm25.get_scores(_tokenize(q))

    ranked = sorted(
        zip(scores, features),
        key=lambda x: x[0],
        reverse=True,
    )

    results = [
        {
            "id":          f["id"],
            "name":        f["name"],
            "description": f.get("description", ""),
            "domain":      f.get("domain", ""),
            "confidence":  f.get("confidence", 1.0),
            "score":       round(float(score), 3),
        }
        for score, f in ranked[:limit]
        if score > 0
    ]

    return {"results": results, "query": q}
