"""
AI Chat — Phase 3.

Three answer strategies:
  1. Graph-native  — structured questions answered directly from Neo4j (no LLM)
  2. LLM stream    — compressed graph context + Claude when credits available
  3. Fallback      — graph-only summary when LLM unavailable
"""
import re
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from companion.graph.compressor import compress, impact_context

router = APIRouter()


class ChatMessage(BaseModel):
    question: str
    feature_id: str | None = None


_IMPACT_RE = [r"what breaks", r"what.{0,20}depend", r"impact.{0,20}(of|if)",
              r"if.{0,40}change", r"blast radius", r"affected.{0,20}by"]
_LIST_RE   = [r"list.{0,20}feature", r"show.{0,20}feature",
              r"what.{0,20}feature", r"which.{0,20}feature", r"all feature"]
_DOMAINS   = ["auth", "billing", "workflow", "data", "api", "infra"]


def _intent(q: str) -> str:
    ql = q.lower()
    if any(re.search(p, ql) for p in _IMPACT_RE):  return "impact"
    if any(d in ql for d in _DOMAINS) and "feature" in ql: return "domain_filter"
    if any(re.search(p, ql) for p in _LIST_RE):    return "list"
    return "open"


def _extract_feature(q: str, names: list[str]) -> str | None:
    ql = q.lower()
    # Exact substring match first
    hits = [n for n in names if n.lower() in ql]
    if hits:
        return max(hits, key=len)
    # Word-level partial match — any word in the question matches any word in name
    q_words = set(w for w in ql.split() if len(w) > 3)
    scored = []
    for n in names:
        n_words = set(n.lower().split())
        overlap = len(q_words & n_words)
        if overlap:
            scored.append((overlap, n))
    if scored:
        return max(scored)[1]
    return None


def _extract_domain(q: str) -> str | None:
    return next((d for d in _DOMAINS if d in q.lower()), None)


# ── Graph-native answers ──────────────────────────────────────────────────────

def _answer_impact(question: str, features: list, relationships: list) -> str:
    target = _extract_feature(question, [f["name"] for f in features])

    # Domain-level impact — "what breaks if auth changes?"
    if not target:
        domain = _extract_domain(question)
        if domain:
            domain_features = [f for f in features if f.get("domain") == domain]
            if domain_features:
                lines = [f"**Impact of changing all `{domain}` features:**\n"]
                all_affected: set[str] = set()
                for df in domain_features:
                    ctx = impact_context(df["name"], features, relationships)
                    for d in ctx.get("direct_dependents", []) + ctx.get("transitive_dependents", []):
                        all_affected.add(d["name"])
                lines.append(f"Auth features: {', '.join(f['name'] for f in domain_features)}\n")
                if all_affected:
                    lines.append(f"**Features that would break ({len(all_affected)}):**")
                    for name in sorted(all_affected):
                        lines.append(f"- {name}")
                else:
                    lines.append("No downstream dependents found.")
                return "\n".join(lines)
        return "Couldn't identify the feature. Try: *What breaks if Invoice Fee Calculation changes?*"

    ctx = impact_context(target, features, relationships)
    if "error" in ctx:
        return ctx["error"]

    lines = [f"**Impact analysis: {ctx['feature']}**", f"_{ctx['description']}_", ""]

    if ctx["direct_dependents"]:
        lines.append(f"**Direct dependents ({len(ctx['direct_dependents'])}):**")
        for d in ctx["direct_dependents"]:
            lines.append(f"- **{d['name']}** `{d['domain']}` — {d['description'][:90]}")
    else:
        lines.append("✓ No direct dependents — safe to change in isolation.")

    if ctx["transitive_dependents"]:
        lines += ["", f"**Also affected ({len(ctx['transitive_dependents'])} transitive):**"]
        for d in ctx["transitive_dependents"][:6]:
            lines.append(f"- {d['name']} (depth {d['depth']})")
        if len(ctx["transitive_dependents"]) > 6:
            lines.append(f"- …and {len(ctx['transitive_dependents']) - 6} more")

    lines += ["", f"**Total blast radius: {ctx['total_blast_radius']} feature(s)**"]
    return "\n".join(lines)


def _answer_list(question: str, features: list) -> str:
    domain = _extract_domain(question)
    filtered = [f for f in features if not domain or f.get("domain") == domain]
    if not filtered:
        return f"No features found{' in domain ' + domain if domain else ''}."

    by_domain: dict[str, list] = {}
    for f in filtered:
        by_domain.setdefault(f.get("domain", "unknown"), []).append(f)

    lines = [f"**{len(filtered)} features{' — ' + domain if domain else ''}:**", ""]
    for d, feats in sorted(by_domain.items()):
        lines.append(f"**{d.capitalize()}**")
        for f in feats:
            lines.append(f"- {f['name']} ({int(f.get('confidence', 1.0) * 100)}%)")
        lines.append("")
    return "\n".join(lines)


# ── LLM with compressed context ───────────────────────────────────────────────

def _llm_stream(question: str, compressed: dict[str, Any]):
    try:
        import anthropic
        client = anthropic.Anthropic()

        ctx = (
            f"Repository has {compressed['stats']['total_features']} features across "
            f"domains: {', '.join(compressed['domain_clusters'].keys())}.\n\n"
            "Key features:\n" +
            "\n".join(
                f"- {s['name']} ({s['domain']}): {s['description'][:100]}"
                + (f" | needs: {', '.join(s['depends_on'][:3])}" if s['depends_on'] else "")
                for s in compressed["feature_summaries"][:15]
            ) +
            "\n\nDependencies:\n" +
            "\n".join(f"  {r['from']} → {r['to']}" for r in compressed["relationships"][:25])
        )

        def stream():
            with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                system=(
                    "You are a code intelligence assistant. Answer concisely using the "
                    "feature graph context. Reference specific feature names. Be direct."
                ),
                messages=[{"role": "user", "content": f"Graph:\n{ctx}\n\nQ: {question}"}],
            ) as s:
                for text in s.text_stream:
                    yield text

        return stream
    except Exception:
        return None


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/")
async def chat(msg: ChatMessage, request: Request):
    engine = request.app.state.engine

    features     = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 200")
    relationships = await engine.neo4j.query(
        "MATCH (a)-[r]->(b) RETURN a.id AS source_id, b.id AS target_id, type(r) AS kind LIMIT 500"
    )

    intent = _intent(msg.question)

    if intent == "impact":
        return {"answer": _answer_impact(msg.question, features, relationships), "source": "graph"}

    if intent in ("list", "domain_filter"):
        return {"answer": _answer_list(msg.question, features), "source": "graph"}

    # Open question — compressed context + LLM
    compressed = compress(features, relationships, query=msg.question)
    stream_fn  = _llm_stream(msg.question, compressed)
    if stream_fn:
        return StreamingResponse(stream_fn(), media_type="text/plain")

    # No LLM — graph summary fallback
    top = compressed["feature_summaries"][:6]
    answer = (
        f"Graph has {compressed['stats']['total_features']} features. Most relevant:\n\n"
        + "\n".join(f"- **{s['name']}** ({s['domain']}): {s['description'][:100]}" for s in top)
        + "\n\n_Add Anthropic credits for richer answers, or ask 'What breaks if X changes?'_"
    )
    return {"answer": answer, "source": "graph"}
