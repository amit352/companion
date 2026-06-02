"""Agent 1: Discover files, detect languages and frameworks."""
import hashlib
import json
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()

_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".rb": "ruby",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
}

_IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", "coverage", ".pytest_cache",
}

_STATE_FILE = ".feature-graph/scan-state.json"


class ProjectScanner:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self._state_path = repo_path / _STATE_FILE

    async def scan(self, incremental: bool = False) -> dict[str, Any]:
        previous_hashes: dict[str, str] = {}
        if incremental and self._state_path.exists():
            previous_hashes = json.loads(self._state_path.read_text())

        files: list[dict[str, Any]] = []
        language_counts: dict[str, int] = {}
        current_hashes: dict[str, str] = {}

        for path in self._walk():
            lang = _LANGUAGE_MAP.get(path.suffix, "unknown")
            content = path.read_text(errors="ignore")
            file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            rel = str(path.relative_to(self.repo_path))
            current_hashes[rel] = file_hash

            if incremental and previous_hashes.get(rel) == file_hash:
                continue

            files.append({
                "path": rel,
                "abs_path": str(path),
                "language": lang,
                "size_bytes": path.stat().st_size,
                "hash": file_hash,
            })
            language_counts[lang] = language_counts.get(lang, 0) + 1

        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(current_hashes))

        log.info(
            "scan_complete",
            total=len(files),
            languages=list(language_counts.keys()),
            incremental=incremental,
        )
        return {
            "files": files,
            "language_counts": language_counts,
            "repo_path": str(self.repo_path),
        }

    def _walk(self):
        for path in self.repo_path.rglob("*"):
            if any(part in _IGNORE_DIRS for part in path.parts):
                continue
            if path.is_file() and path.suffix in _LANGUAGE_MAP:
                yield path
