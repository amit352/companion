"""
Chat feedback storage — closes the learning loop.

Every chat exchange can be rated. Wrong answers with corrections feed back
into feature extraction accuracy over time (Phase 2 accuracy loop).
"""
import os
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class FeedbackVerdict(StrEnum):
    CORRECT = "correct"
    WRONG   = "wrong"
    PARTIAL = "partial"


class ChatFeedbackRequest(BaseModel):
    question:            str
    answer:              str
    source:              str           # "graph" | "llm"
    verdict:             FeedbackVerdict
    correction:          str | None = None
    features_referenced: list[str] = []


class ChatFeedbackResponse(BaseModel):
    id:      str
    verdict: FeedbackVerdict
    stored:  bool


def _get_conn():
    import psycopg2
    dsn = os.environ.get("POSTGRES_DSN", "postgresql://companion:companion-dev@localhost:5433/companion")
    return psycopg2.connect(dsn)


@router.post("/feedback", response_model=ChatFeedbackResponse)
async def store_feedback(body: ChatFeedbackRequest) -> ChatFeedbackResponse:
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute(
            """
            INSERT INTO chat_feedback
              (question, answer, source, verdict, correction, features_referenced)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                body.question,
                body.answer,
                body.source,
                body.verdict.value,
                body.correction,
                body.features_referenced,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return ChatFeedbackResponse(id=str(row[0]), verdict=body.verdict, stored=True)
    except Exception as e:
        # Non-fatal — feedback storage should never break the chat
        return ChatFeedbackResponse(id="", verdict=body.verdict, stored=False)


@router.get("/feedback/summary")
async def feedback_summary() -> dict[str, Any]:
    """Quick accuracy overview — how many answers were correct vs wrong."""
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute("""
            SELECT source, verdict, COUNT(*) as n
            FROM chat_feedback
            GROUP BY source, verdict
            ORDER BY source, verdict
        """)
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*) FROM chat_feedback")
        total = cur.fetchone()[0]
        cur.close(); conn.close()
        return {
            "total": total,
            "breakdown": [{"source": r[0], "verdict": r[1], "count": r[2]} for r in rows],
        }
    except Exception:
        return {"total": 0, "breakdown": [], "error": "Postgres not available"}
