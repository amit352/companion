"""Agent 6: Generate compressed AI contexts (Section 10, target 70% token reduction)."""
from typing import Any

import structlog

from feature_graph.sdk.base.plugin_base import PluginContext, PluginType
from feature_graph.sdk.registry import PluginRegistry

log = structlog.get_logger()


class AICompressorAgent:
    def __init__(self, plugin_registry: PluginRegistry) -> None:
        self._registry = plugin_registry

    async def compress(
        self,
        features: dict[str, Any],
        graph_summary: dict[str, Any],
    ) -> dict[str, Any]:
        compressors = self._registry.get_by_type(PluginType.AI_COMPRESSION)

        if not compressors:
            log.warning("no_compression_plugins_registered")
            return {"compressed": False, "compression_ratio": 0.0}

        compressor = compressors[0]
        ctx = PluginContext(repo_path="", graph_session_id="")
        result = await compressor.execute(ctx, {
            "feature_graph": {**features, "graph_summary": graph_summary},
        })

        log.info(
            "compression_done",
            ratio=result.get("compression_ratio", 0),
            raw_tokens=result.get("raw_token_estimate", 0),
            compressed_tokens=result.get("compressed_token_estimate", 0),
        )
        return result
