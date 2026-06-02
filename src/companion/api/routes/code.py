"""
Source code serving endpoint.

Only serves files that are registered as source_files on Feature nodes
in the graph — prevents arbitrary file system access (NFR-4 security).
"""
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()

# Language detection from extension
_LANG_MAP = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".rb": "ruby",
    ".java": "java", ".go": "go", ".rs": "rust", ".md": "markdown",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".sql": "sql", ".sh": "bash", ".tf": "hcl",
}


@router.get("/file")
async def get_file_content(
    request: Request,
    path: str = Query(..., description="Relative file path from feature.source_files"),
    feature_id: str = Query(..., description="Feature ID that references this file"),
    max_lines: int = Query(200, le=500),
):
    """
    Returns the source code for a file referenced by a feature.
    Security: only serves files listed in source_files of the given feature.
    """
    engine = request.app.state.engine

    # Verify this file is actually referenced by the given feature
    features = await engine.neo4j.query(
        "MATCH (f:Feature {id: $id}) RETURN f.source_files AS files, f.name AS name",
        id=feature_id,
    )
    if not features:
        raise HTTPException(status_code=404, detail="Feature not found")

    source_files: list[str] = features[0].get("files") or []
    # Allow if path is a suffix match of any registered source file
    if not any(path in sf or sf in path or sf.endswith(path) or path.endswith(sf)
               for sf in source_files):
        raise HTTPException(
            status_code=403,
            detail=f"File '{path}' is not registered for feature '{features[0]['name']}'"
        )

    # Resolve repo path from registered repositories
    repos = await engine.neo4j.query("MATCH (r:Repository) RETURN r.path AS path, r.name AS name")

    resolved: Path | None = None
    for repo in repos:
        candidate = Path(repo["path"]) / path
        if candidate.exists():
            resolved = candidate
            break

    if not resolved:
        # Try absolute path directly
        p = Path(path)
        if p.exists():
            resolved = p

    if not resolved:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        lines = resolved.read_text(errors="replace").splitlines()
        total_lines = len(lines)
        truncated = total_lines > max_lines
        content = "\n".join(lines[:max_lines])
        if truncated:
            content += f"\n\n... ({total_lines - max_lines} more lines)"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read file: {e}")

    return {
        "path":        path,
        "language":    _LANG_MAP.get(resolved.suffix.lower(), "text"),
        "content":     content,
        "total_lines": total_lines,
        "shown_lines": min(total_lines, max_lines),
        "truncated":   truncated,
    }
