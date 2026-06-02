"""Agent 2: Parse source files via registered Parser plugins (tree-sitter backed)."""
import asyncio
from typing import Any

import structlog

from feature_graph.sdk.base.plugin_base import PluginContext, PluginType
from feature_graph.sdk.registry import PluginRegistry

log = structlog.get_logger()


class FileAnalyzer:
    def __init__(self, plugin_registry: PluginRegistry, semaphore: asyncio.Semaphore) -> None:
        self._registry = plugin_registry
        self._semaphore = semaphore

    async def analyze(self, file_info: dict[str, Any]) -> dict[str, Any]:
        async with self._semaphore:
            language = file_info["language"]
            parsers = self._registry.get_by_type(PluginType.PARSER)
            parser = next(
                (p for p in parsers if language in p.manifest.languages),
                None,
            )

            if parser is None:
                log.debug("no_parser_for_language", language=language, file=file_info["path"])
                return {
                    "file": file_info["path"],
                    "language": language,
                    "symbols": [],
                    "dependencies": [],
                    "ast": [],
                }

            try:
                abs_path = file_info["abs_path"]
                source = open(abs_path, errors="ignore").read()
                ctx = PluginContext(repo_path=file_info["abs_path"], graph_session_id="")
                result = await parser.execute(ctx, {"file_path": abs_path, "source": source})
                return {"file": file_info["path"], "language": language, **result}
            except Exception as exc:
                log.warning("file_analysis_failed", file=file_info["path"], error=str(exc))
                return {"file": file_info["path"], "language": language, "error": str(exc)}
