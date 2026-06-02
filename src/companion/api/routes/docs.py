"""
Phase 5 — Documentation generation.
FR-10: export as Markdown, HTML, PDF, JSON.

POST /api/v1/docs/generate
  ?format=markdown|html|pdf|json  (default: markdown)
  body: { doc_type: srs|adr|readme, repo_name: str }
"""
import io
import json
from enum import StrEnum

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, HTMLResponse, Response
from pydantic import BaseModel

from companion.graph.compressor import compress

router = APIRouter()

# ── Types ─────────────────────────────────────────────────────────────────────

class DocType(StrEnum):
    SRS    = "srs"
    ADR    = "adr"
    README = "readme"

class ExportFormat(StrEnum):
    MARKDOWN = "markdown"
    HTML     = "html"
    PDF      = "pdf"
    JSON     = "json"

class GenerateRequest(BaseModel):
    doc_type:  DocType      = DocType.SRS
    format:    ExportFormat = ExportFormat.MARKDOWN
    repo_name: str          = "Repository"


# ── HTML page template ────────────────────────────────────────────────────────

_HTML_WRAPPER = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --bg:#0f172a; --fg:#e2e8f0; --muted:#94a3b8; --accent:#60a5fa;
            --border:#1e293b; --code-bg:#1e293b; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--fg); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          line-height:1.7; padding:2rem; max-width:860px; margin:0 auto; }}
  h1 {{ font-size:2rem; color:var(--accent); margin-bottom:.5rem; }}
  h2 {{ font-size:1.35rem; color:var(--fg); margin:2rem 0 .75rem; border-bottom:1px solid var(--border); padding-bottom:.4rem; }}
  h3,h4 {{ font-size:1.05rem; color:var(--muted); margin:1.25rem 0 .5rem; }}
  p,li {{ color:#cbd5e1; }}
  ul {{ padding-left:1.5rem; }}
  code {{ background:var(--code-bg); padding:.15rem .4rem; border-radius:4px; font-size:.85em; color:#7dd3fc; }}
  pre  {{ background:var(--code-bg); padding:1rem; border-radius:8px; overflow-x:auto; margin:.75rem 0; }}
  pre code {{ padding:0; }}
  strong {{ color:var(--fg); }}
  em {{ color:var(--muted); font-style:italic; }}
  table {{ width:100%; border-collapse:collapse; margin:1rem 0; }}
  th,td {{ border:1px solid var(--border); padding:.5rem .75rem; text-align:left; }}
  th {{ background:#1e293b; color:var(--fg); }}
  hr {{ border:none; border-top:1px solid var(--border); margin:2rem 0; }}
  .meta {{ color:var(--muted); font-size:.85rem; margin-bottom:2rem; }}
  @media print {{
    body {{ background:#fff; color:#111; }}
    h1 {{ color:#1d4ed8; }}
    h2,h3,h4 {{ color:#334155; }}
    code,pre {{ background:#f1f5f9; color:#0f172a; }}
    p,li {{ color:#334155; }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>"""


def _md_to_html(md: str, title: str) -> str:
    import markdown as md_lib
    body = md_lib.markdown(
        md,
        extensions=["tables", "fenced_code", "toc", "nl2br"],
    )
    return _HTML_WRAPPER.format(title=title, body=body)


def _s(text: str) -> str:
    """Sanitize text for fpdf2 Latin-1 Helvetica font (no smart quotes)."""
    return (str(text)
            .replace("—", "-").replace("–", "-")
            .replace("'", "'").replace("'", "'")
            .replace(""", '"').replace(""", '"')
            .replace("…", "...").replace("•", "*")
            .encode("latin-1", "replace").decode("latin-1"))


def _md_to_pdf(md: str, title: str, repo_name: str) -> bytes:
    """Generate PDF directly from structured data — bypasses markdown parsing."""
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    W = pdf.w - 30  # usable width

    def h1(text: str):
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(30, 90, 200)
        pdf.multi_cell(W, 10, _s(text))
        pdf.ln(1)

    def h2(text: str):
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(W, 8, _s(text))
        pdf.set_draw_color(200, 200, 200)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(2)
        pdf.set_text_color(60, 60, 60)

    def h3(text: str):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 90, 200)
        pdf.multi_cell(W, 7, _s(text))
        pdf.set_text_color(60, 60, 60)

    def body(text: str):
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(W, 6, _s(text))

    def bullet(text: str):
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.set_x(20)
        pdf.multi_cell(W - 5, 5.5, _s(f"* {text}"))

    # Parse and render
    for line in md.splitlines():
        if line.startswith("# "):
            h1(line[2:])
        elif line.startswith("## "):
            h2(line[3:])
        elif line.startswith("### ") or line.startswith("#### "):
            h3(line.lstrip("#").strip().replace("**", "").replace("_", ""))
        elif line.startswith("- ") or line.startswith("* "):
            bullet(line[2:].replace("**", "").replace("`", ""))
        elif line.startswith("---"):
            pdf.ln(2)
        elif line.strip().startswith("*") and line.strip().endswith("*"):
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(120, 120, 120)
            pdf.multi_cell(W, 6, _s(line.strip().strip("*")))
        elif line.strip():
            body(line.replace("**", "").replace("`", "").replace("_", ""))
        else:
            pdf.ln(1)

    return bytes(pdf.output())


def _graph_to_json(features: list, rels: list, node_counts: list,
                   compressed: dict, repo_name: str) -> dict:
    """Machine-readable JSON export — full graph data + compression stats."""
    return {
        "meta": {
            "repo_name":    repo_name,
            "generated_by": "Companion",
            "srs_version":  "1.0",
        },
        "summary": {
            "total_features":      compressed["stats"]["total_features"],
            "total_relationships": compressed["stats"]["total_relationships"],
            "domains":             list(compressed["domain_clusters"].keys()),
            "compression_ratio":   compressed["stats"]["compression_ratio"],
        },
        "features":        features,
        "relationships":   rels,
        "node_counts":     node_counts,
        "semantic_clusters": compressed.get("semantic_clusters", []),
        "feature_summaries": compressed.get("feature_summaries", []),
    }


# ── Markdown generators (unchanged) ──────────────────────────────────────────

def _generate_srs(name: str, features: list, compressed: dict) -> str:
    stats = compressed["stats"]
    by_domain: dict[str, list] = {}
    for f in features:
        by_domain.setdefault(f.get("domain", "unknown"), []).append(f)

    lines = [
        f"# Software Requirements Specification",
        f"## {name}",
        f"",
        f"*Generated by Companion — {stats['total_features']} features, "
        f"{stats['total_relationships']} relationships*",
        f"",
        f"---",
        f"",
        f"## 1. Overview",
        f"",
        f"**{name}** contains **{stats['total_features']} business features** across "
        f"**{len(by_domain)} domains**: "
        f"{', '.join(f'{d} ({len(v)})' for d, v in sorted(by_domain.items(), key=lambda x: -len(x[1])))}.",
        f"",
        f"---",
        f"",
        f"## 2. Functional Requirements",
        f"",
    ]
    fr_num = 1
    for domain, domain_features in sorted(by_domain.items()):
        lines.append(f"### 2.{list(by_domain.keys()).index(domain)+1} {domain.replace('-',' ').title()} Domain")
        lines.append("")
        for f in sorted(domain_features, key=lambda x: -x.get("confidence", 0)):
            conf = int(f.get("confidence", 1.0) * 100)
            lines += [
                f"**FR-{fr_num:02d} {f['name']}**  ",
                f"_{f.get('description', '')}_ (confidence: {conf}%)",
                f"",
                f"- Source: `{'`, `'.join(f.get('source_files', [])[:2])}`",
            ]
            if f.get("tags"):
                lines.append(f"- Tags: {', '.join(f['tags'])}")
            lines.append("")
            fr_num += 1

    lines += [
        f"---", f"",
        f"## 3. Feature Dependencies", f"",
        f"```",
        *[f"{r['from']}  →  {r['to']}" for r in compressed.get("relationships", [])[:30]],
        "```", "",
    ]
    return "\n".join(lines)


def _generate_readme(name: str, features: list, compressed: dict) -> str:
    stats = compressed["stats"]
    top   = sorted(features, key=lambda f: -f.get("confidence", 0))[:8]
    by_domain: dict[str, int] = {}
    for f in features:
        by_domain[f.get("domain", "unknown")] = by_domain.get(f.get("domain","unknown"), 0) + 1

    lines = [
        f"# {name}",
        f"",
        f"> Generated by [Companion](https://github.com/amit352/companion)",
        f"",
        f"## Overview",
        f"",
        f"**{stats['total_features']} business features** across "
        f"**{len(by_domain)} domains**: "
        f"{', '.join(f'{d} ({n})' for d, n in sorted(by_domain.items(), key=lambda x: -x[1]))}.",
        f"",
        f"## Key Features",
        f"",
    ]
    for f in top:
        lines.append(f"- **{f['name']}** — {f.get('description', '')}")
    lines += ["", "## Domain Breakdown", "", "| Domain | Features |", "|--------|---------|"]
    for d, n in sorted(by_domain.items(), key=lambda x: -x[1]):
        lines.append(f"| {d.title()} | {n} |")
    lines.append("")
    return "\n".join(lines)


def _generate_adr(name: str, compressed: dict) -> str:
    top = compressed["feature_summaries"][:5]
    lines = [
        f"# Architecture Decision Record — {name}",
        f"",
        f"**Status:** Accepted  ",
        f"**Generated by:** Companion",
        f"",
        f"## Context",
        f"",
        f"{name} has {compressed['stats']['total_features']} features with "
        f"{compressed['stats']['total_relationships']} dependencies.",
        f"",
        f"## Key Components",
        f"",
    ]
    for s in top:
        deps = ", ".join(s.get("depends_on", [])[:3])
        lines += [
            f"### {s['name']}",
            s.get("description", ""),
            *([ f"*Depends on:* {deps}" ] if deps else []),
            "",
        ]
    lines += ["## Consequences", "", "- High in-degree nodes are architectural risk points", ""]
    return "\n".join(lines)


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.get("/sequence")
async def sequence_diagram(request: Request, feature_id: str | None = None):
    """
    Generate a Mermaid sequence diagram from feature dependencies.
    Shows the flow: who calls whom in the feature graph.
    """
    engine = request.app.state.engine

    if feature_id:
        # Diagram for one feature and its connections
        rels = await engine.neo4j.query(
            """
            MATCH (a)-[r:DEPENDS_ON]->(b)
            WHERE a.id = $id OR b.id = $id
            RETURN a.name AS from, b.name AS to
            LIMIT 20
            """,
            id=feature_id,
        )
        title = "Feature Flow"
    else:
        # Top-level flow across all features
        rels = await engine.neo4j.query(
            """
            MATCH (a:Feature)-[r:DEPENDS_ON]->(b:Feature)
            RETURN a.name AS from, b.name AS to
            LIMIT 30
            """
        )
        title = "System Flow"

    def safe(name: str) -> str:
        return name.replace("(", "").replace(")", "").replace(" ", "_").replace("-", "_")[:30]

    lines = [
        "```mermaid",
        "sequenceDiagram",
        f"    %% {title}",
    ]

    seen_parts: set[str] = set()
    for r in rels:
        src = r.get("from") or ""
        tgt = r.get("to") or ""
        if not src or not tgt:
            continue
        s, t = safe(src), safe(tgt)
        # Declare participants once
        for label, alias in [(src, s), (tgt, t)]:
            if alias not in seen_parts:
                lines.append(f"    participant {alias} as {label[:25]}")
                seen_parts.add(alias)
        lines.append(f"    {s}->>+{t}: depends on")

    lines.append("```")

    if len(seen_parts) < 2:
        return PlainTextResponse("```mermaid\nsequenceDiagram\n    Note: No relationships found\n```")

    return PlainTextResponse("\n".join(lines))


@router.post("/generate")
async def generate_doc(req: GenerateRequest, request: Request):
    engine = request.app.state.engine

    features     = await engine.neo4j.query("MATCH (f:Feature) RETURN f LIMIT 200")
    relationships = await engine.neo4j.query(
        "MATCH (a)-[r]->(b) RETURN a.id AS source_id, b.id AS target_id, type(r) AS kind LIMIT 500"
    )
    node_counts  = await engine.neo4j.query(
        "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS n ORDER BY n DESC"
    )
    compressed = compress(features, relationships)

    # Generate markdown first
    if req.doc_type == DocType.SRS:
        md = _generate_srs(req.repo_name, features, compressed)
        title = f"SRS — {req.repo_name}"
    elif req.doc_type == DocType.README:
        md = _generate_readme(req.repo_name, features, compressed)
        title = f"README — {req.repo_name}"
    else:
        md = _generate_adr(req.repo_name, compressed)
        title = f"ADR — {req.repo_name}"

    # Return in requested format
    if req.format == ExportFormat.MARKDOWN:
        return PlainTextResponse(md, media_type="text/markdown")

    if req.format == ExportFormat.HTML:
        html = _md_to_html(md, title)
        return HTMLResponse(html)

    if req.format == ExportFormat.PDF:
        pdf_bytes = _md_to_pdf(md, title, req.repo_name)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{req.doc_type}.pdf"'},
        )

    if req.format == ExportFormat.JSON:
        data = _graph_to_json(features, relationships, node_counts, compressed, req.repo_name)
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{req.doc_type}.json"'},
        )
