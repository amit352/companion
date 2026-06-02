"""
Human feedback loop for feature clustering accuracy (Phase 2).
POST /api/v1/features/{id}/feedback — correct or confirm a detected feature.
"""
from enum import StrEnum

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class FeedbackVerdict(StrEnum):
    CORRECT = "correct"
    WRONG_DOMAIN = "wrong_domain"
    MERGE = "merge"
    SPLIT = "split"
    NOT_A_FEATURE = "not_a_feature"


class FeedbackRequest(BaseModel):
    verdict: FeedbackVerdict
    corrected_name: str | None = None
    corrected_domain: str | None = None
    corrected_description: str | None = None
    merge_into_id: str | None = None
    notes: str | None = None


class FeedbackResponse(BaseModel):
    feature_id: str
    verdict: FeedbackVerdict
    applied: bool
    message: str


@router.post("/{feature_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(feature_id: str, body: FeedbackRequest, request: Request):
    engine = request.app.state.engine

    # Verify feature exists
    records = await engine.neo4j.query(
        "MATCH (f:Feature {id: $id}) RETURN f", id=feature_id
    )
    if not records:
        raise HTTPException(status_code=404, detail="Feature not found")

    if body.verdict == FeedbackVerdict.NOT_A_FEATURE:
        await engine.neo4j.query(
            "MATCH (f:Feature {id: $id}) SET f.hidden = true, f.feedback = 'not_a_feature'",
            id=feature_id,
        )
        return FeedbackResponse(
            feature_id=feature_id,
            verdict=body.verdict,
            applied=True,
            message="Feature marked as false positive and hidden from graph",
        )

    if body.verdict == FeedbackVerdict.WRONG_DOMAIN and body.corrected_domain:
        await engine.neo4j.query(
            "MATCH (f:Feature {id: $id}) SET f.domain = $domain, f.feedback = 'corrected'",
            id=feature_id,
            domain=body.corrected_domain,
        )

    if body.corrected_name:
        await engine.neo4j.query(
            "MATCH (f:Feature {id: $id}) SET f.name = $name",
            id=feature_id,
            name=body.corrected_name,
        )

    if body.corrected_description:
        await engine.neo4j.query(
            "MATCH (f:Feature {id: $id}) SET f.description = $desc",
            id=feature_id,
            desc=body.corrected_description,
        )

    if body.verdict == FeedbackVerdict.MERGE and body.merge_into_id:
        # Redirect all relationships from this feature to the target, then hide it
        await engine.neo4j.query(
            """
            MATCH (src:Feature {id: $src_id})-[r]->(n)
            MATCH (tgt:Feature {id: $tgt_id})
            MERGE (tgt)-[:DEPENDS_ON]->(n)
            """,
            src_id=feature_id,
            tgt_id=body.merge_into_id,
        )
        await engine.neo4j.query(
            "MATCH (f:Feature {id: $id}) SET f.hidden = true, f.merged_into = $tgt",
            id=feature_id,
            tgt=body.merge_into_id,
        )

    # Boost confidence on confirmed features
    if body.verdict == FeedbackVerdict.CORRECT:
        await engine.neo4j.query(
            "MATCH (f:Feature {id: $id}) SET f.confidence = min(1.0, f.confidence + 0.1), f.feedback = 'confirmed'",
            id=feature_id,
        )

    return FeedbackResponse(
        feature_id=feature_id,
        verdict=body.verdict,
        applied=True,
        message=f"Feedback '{body.verdict}' applied",
    )
