"""
AI Chat Interface — FR-7, Section 11.2.
Users can ask natural language questions about the codebase, answered using
compressed graph context to minimize token usage.
"""
import json

import anthropic
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

_SYSTEM = """You are FeatureGraph, an AI assistant that answers questions about codebases
using a structured feature knowledge graph. You receive compressed graph context and answer
questions about architecture, dependencies, and impact analysis.

Be concise and specific. Reference feature names and service names from the graph.
When asked about impact, always mention downstream dependents."""


class ChatMessage(BaseModel):
    question: str
    feature_id: str | None = None  # optional: scope to a specific feature's context


@router.post("/")
async def chat(msg: ChatMessage, request: Request):
    engine = request.app.state.engine
    client = anthropic.Anthropic()

    # Fetch compressed context for the question
    if msg.feature_id:
        subgraph = await engine.neo4j.get_feature_subgraph(msg.feature_id, depth=3)
        context = json.dumps(subgraph)[:8000]
    else:
        features = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 30")
        context = json.dumps({"features": features})[:8000]

    def stream():
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Graph context:\n{context}\n\nQuestion: {msg.question}",
            }],
        ) as stream:
            for text in stream.text_stream:
                yield text

    return StreamingResponse(stream(), media_type="text/plain")
