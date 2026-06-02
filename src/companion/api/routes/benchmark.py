"""
Accuracy benchmark harness — Phase 6 success metrics (Section 14).

Measures:
  - Feature extraction accuracy (precision/recall vs labelled ground truth)
  - Compression ratio (raw token estimate vs compressed)
  - Dependency extraction accuracy (edges present vs total expected)

POST /api/v1/benchmark/run   — compare extracted features against ground truth
GET  /api/v1/benchmark/stats — current graph statistics
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel

from companion.graph.compressor import compress

router = APIRouter()


class GroundTruthFeature(BaseModel):
    name: str
    domain: str


class BenchmarkRequest(BaseModel):
    ground_truth: list[GroundTruthFeature]
    fuzzy_match: bool = True    # allow partial name matches


class BenchmarkResponse(BaseModel):
    precision:          float   # extracted that are correct / all extracted
    recall:             float   # correct extracted / all ground truth
    f1:                 float
    extracted_count:    int
    ground_truth_count: int
    matched:            list[str]
    missed:             list[str]
    extra:              list[str]
    compression_ratio:  float
    token_reduction_pct: float


def _names_match(a: str, b: str, fuzzy: bool) -> bool:
    if not fuzzy:
        return a.lower() == b.lower()
    al, bl = a.lower(), b.lower()
    return al == bl or al in bl or bl in al or any(
        w in bl for w in al.split() if len(w) > 3
    )


@router.post("/run", response_model=BenchmarkResponse)
async def run_benchmark(req: BenchmarkRequest, request: Request) -> BenchmarkResponse:
    engine    = request.app.state.engine
    features  = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 500")
    rels      = await engine.neo4j.query(
        "MATCH (a)-[r]->(b) RETURN a.id AS source_id, b.id AS target_id, type(r) AS kind LIMIT 1000"
    )

    extracted_names = [f["name"] for f in features]
    gt_names        = [gt.name for gt in req.ground_truth]

    matched, missed, extra = [], [], []

    for gt in gt_names:
        if any(_names_match(gt, e, req.fuzzy_match) for e in extracted_names):
            matched.append(gt)
        else:
            missed.append(gt)

    for e in extracted_names:
        if not any(_names_match(e, gt, req.fuzzy_match) for gt in gt_names):
            extra.append(e)

    precision = len(matched) / max(len(extracted_names), 1)
    recall    = len(matched) / max(len(gt_names), 1)
    f1        = 2 * precision * recall / max(precision + recall, 0.0001)

    compressed = compress(features, rels)
    stats      = compressed["stats"]
    ratio      = stats.get("compression_ratio", 0)

    return BenchmarkResponse(
        precision=round(precision, 3),
        recall=round(recall, 3),
        f1=round(f1, 3),
        extracted_count=len(extracted_names),
        ground_truth_count=len(gt_names),
        matched=matched,
        missed=missed,
        extra=extra[:20],
        compression_ratio=round(ratio, 3),
        token_reduction_pct=round(ratio * 100, 1),
    )


@router.get("/stats")
async def graph_stats(request: Request) -> dict:
    """Current graph health metrics — node counts, edge counts, domain distribution."""
    engine = request.app.state.engine

    node_counts = await engine.neo4j.query(
        "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS n ORDER BY n DESC"
    )
    edge_counts = await engine.neo4j.query(
        "MATCH ()-[r]->() RETURN type(r) AS kind, count(r) AS n ORDER BY n DESC"
    )
    domain_dist = await engine.neo4j.query(
        "MATCH (f:Feature) RETURN f.domain AS domain, count(f) AS n ORDER BY n DESC"
    )
    avg_conf = await engine.neo4j.query(
        "MATCH (f:Feature) RETURN round(avg(f.confidence)*100)/100 AS avg_confidence"
    )
    compressed = compress(
        await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 200"),
        await engine.neo4j.query(
            "MATCH (a)-[r]->(b) RETURN a.id AS source_id, b.id AS target_id, type(r) AS kind LIMIT 500"
        ),
    )

    return {
        "node_counts":         node_counts,
        "edge_counts":         edge_counts,
        "domain_distribution": domain_dist,
        "avg_confidence":      avg_conf[0].get("avg_confidence") if avg_conf else None,
        "compression_stats":   compressed["stats"],
        "srs_targets": {
            "feature_clustering_accuracy_target": "80%",
            "dependency_extraction_accuracy_target": "90%",
            "token_reduction_target": "70%",
            "current_compression_ratio": f"{round(compressed['stats'].get('compression_ratio',0)*100)}%",
        },
    }
