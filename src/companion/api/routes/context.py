"""
Context injection API — the bridge between Companion and Claude Code.

Claude Code calls these endpoints to get focused, token-efficient context
instead of reading raw source files. Over time, as the graph grows richer,
the same questions cost fewer and fewer tokens.

Endpoints:
  GET  /api/v1/context/session      — full session startup context (~500 tokens)
  POST /api/v1/context/for-files    — context scoped to specific changed files
  POST /api/v1/context/for-question — context relevant to a natural language question
  POST /api/v1/context/after-edit   — update graph after Claude edits files
"""
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from companion.graph.compressor import compress

router = APIRouter()


# ── Request/response models ────────────────────────────────────────────────────

class FilesContextRequest(BaseModel):
    files: list[str]             # relative paths of files Claude is working on
    question: str | None = None  # optional: what Claude is trying to do

class QuestionContextRequest(BaseModel):
    question: str
    max_tokens: int = 800        # target token budget

class AfterEditRequest(BaseModel):
    files_changed: list[str]
    summary: str = ""            # what Claude changed, in plain English
    repo_path: str = ""


def _token_estimate(text: str) -> int:
    return len(text.split()) * 4 // 3


def _format_context(
    features: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    title: str,
    query: str | None = None,
) -> dict[str, Any]:
    """Build the compact context payload Claude injects at the top of its context window."""
    compressed = compress(features, relationships, query=query)
    stats = compressed["stats"]

    # Build the compact text representation
    lines = [
        f"# Companion Knowledge Graph — {title}",
        f"# {stats['total_features']} features | {stats['total_relationships']} dependencies | {stats.get('compression_ratio', 0)*100:.0f}% compressed",
        f"",
    ]

    # Domain clusters (very compact)
    if compressed["domain_clusters"]:
        lines.append("## Domains")
        for domain, names in sorted(compressed["domain_clusters"].items()):
            lines.append(f"  {domain}: {', '.join(names[:5])}" + (" ..." if len(names) > 5 else ""))
        lines.append("")

    # Top features with dependencies
    lines.append("## Key Features")
    for s in compressed["feature_summaries"][:12]:
        dep_str = f" → needs: {', '.join(s['depends_on'][:2])}" if s['depends_on'] else ""
        lines.append(f"  [{s['domain']}] {s['name']}: {s['description'][:80]}{dep_str}")
    lines.append("")

    # Dependency chains (most important ones)
    if compressed["relationships"]:
        lines.append("## Critical Dependencies")
        for r in compressed["relationships"][:15]:
            lines.append(f"  {r['from']} → {r['to']}")
        lines.append("")

    context_text = "\n".join(lines)

    return {
        "context_text": context_text,
        "token_estimate": _token_estimate(context_text),
        "stats": stats,
        "features_included": len(compressed["feature_summaries"]),
        "usage_hint": (
            "Inject this at the top of your context window. "
            "Use GET /api/v1/context/for-question?q=... for targeted context per query."
        ),
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/session")
async def session_context(request: Request):
    """
    Full session startup context. Call this when starting a Claude Code session
    to get the compressed knowledge graph. ~300-800 tokens depending on repo size.

    Add to CLAUDE.md:
      On session start, call GET http://localhost:8000/api/v1/context/session
      and include the context_text in your initial context.
    """
    engine        = request.app.state.engine
    features      = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 200")
    relationships = await engine.neo4j.query(
        "MATCH (a)-[r]->(b) RETURN a.id AS source_id, b.id AS target_id, type(r) AS kind LIMIT 500"
    )

    # Also get repo info
    repos = await engine.neo4j.query(
        "MATCH (r:Repository) RETURN r.name AS name, r.feature_count AS features, r.last_analyzed AS ts"
    )

    ctx = _format_context(features, relationships, "Repository Knowledge")
    ctx["repositories"] = repos
    ctx["instructions"] = {
        "update_graph": "After making significant changes, call POST /api/v1/context/after-edit",
        "targeted_context": "For focused work, call POST /api/v1/context/for-files with the files you're editing",
        "impact_analysis": 'Ask the AI Chat: "What breaks if <feature> changes?"',
    }
    return ctx


@router.post("/for-files")
async def context_for_files(req: FilesContextRequest, request: Request):
    """
    Get context scoped to specific files. Use when Claude is working on
    a subset of the codebase — returns only the features that reference
    those files, plus their immediate dependencies.
    """
    engine = request.app.state.engine

    # Find features that reference these files
    features = await engine.neo4j.query(
        """
        MATCH (f:Feature)
        WHERE any(sf IN f.source_files WHERE any(path IN $paths WHERE sf CONTAINS path OR path CONTAINS sf))
        RETURN f
        LIMIT 50
        """,
        paths=req.files,
    )

    # If no direct matches, fall back to question-based compression
    if not features and req.question:
        features = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 200")

    feature_ids = [f["id"] for f in features]
    relationships = await engine.neo4j.query(
        """
        MATCH (a)-[r]->(b)
        WHERE a.id IN $ids OR b.id IN $ids
        RETURN a.id AS source_id, b.id AS target_id, type(r) AS kind
        LIMIT 200
        """,
        ids=feature_ids,
    ) if feature_ids else []

    title = f"Context for {len(req.files)} file(s)"
    return _format_context(features, relationships, title, query=req.question)


@router.post("/for-question")
async def context_for_question(req: QuestionContextRequest, request: Request):
    """
    Get context optimized for a specific question. Uses BM25 to find the
    most relevant features, then compresses around them.
    """
    engine   = request.app.state.engine
    features = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 200")
    rels     = await engine.neo4j.query(
        "MATCH (a)-[r]->(b) RETURN a.id AS source_id, b.id AS target_id, type(r) AS kind LIMIT 500"
    )

    # BM25 rank to find relevant features
    from rank_bm25 import BM25Okapi
    def tok(t): return t.lower().replace("-"," ").split()
    corpus = [tok(f.get("name","") + " " + f.get("description","") + " " + " ".join(f.get("tags",[]))) for f in features]

    if corpus:
        bm25   = BM25Okapi(corpus)
        scores = bm25.get_scores(tok(req.question))
        ranked = sorted(zip(scores, features), key=lambda x: -x[0])
        # Take top features by relevance, biased toward max_tokens budget
        relevant = [f for s, f in ranked if s > 0][:20]
    else:
        relevant = features[:20]

    rel_ids  = {f["id"] for f in relevant}
    rel_rels = [r for r in rels if r["source_id"] in rel_ids or r["target_id"] in rel_ids]

    return _format_context(relevant, rel_rels, "Focused Context", query=req.question)


@router.post("/after-edit")
async def after_edit(req: AfterEditRequest, request: Request):
    """
    Called after Claude makes significant changes to files.
    Records the edit in graph history and triggers incremental re-analysis.
    """
    import structlog
    log = structlog.get_logger()
    engine = request.app.state.engine

    # Record the edit event in Neo4j
    if req.files_changed:
        await engine.neo4j.query(
            """
            MERGE (e:EditEvent {id: randomUUID()})
            SET e.files = $files, e.summary = $summary,
                e.timestamp = datetime(), e.repo_path = $repo
            """,
            files=req.files_changed,
            summary=req.summary or "No summary provided",
            repo=req.repo_path,
        )

    log.info("after_edit_recorded",
             files=len(req.files_changed), summary=req.summary[:80] if req.summary else "")

    # Return updated context for the changed files
    return await context_for_files(
        FilesContextRequest(files=req.files_changed, question=req.summary),
        request,
    )
