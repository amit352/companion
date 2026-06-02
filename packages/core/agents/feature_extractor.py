"""Agent 3: LLM-powered feature extraction from parsed structures."""
from typing import Any

import structlog

from feature_graph.sdk.base.plugin_base import PluginContext, PluginType
from feature_graph.sdk.registry import PluginRegistry

log = structlog.get_logger()


class FeatureExtractorAgent:
    def __init__(self, plugin_registry: PluginRegistry) -> None:
        self._registry = plugin_registry

    async def extract(
        self, parse_results: list[dict[str, Any]], repo_path: str
    ) -> dict[str, Any]:
        extractors = self._registry.get_by_type(PluginType.FEATURE_EXTRACTOR)

        if not extractors:
            log.warning("no_feature_extractors_registered")
            return {"features": [], "relationships": [], "ownership": []}

        all_symbols = [s for r in parse_results for s in r.get("symbols", [])]
        all_deps = [d for r in parse_results for d in r.get("dependencies", [])]
        source_context = f"Repository: {repo_path}\nFiles: {len(parse_results)}"

        merged_features: list[Any] = []
        merged_relationships: list[Any] = []
        merged_ownership: list[Any] = []

        for extractor in extractors:
            ctx = PluginContext(repo_path=repo_path, graph_session_id="")
            result = await extractor.execute(ctx, {
                "symbols": all_symbols,
                "dependencies": all_deps,
                "source_context": source_context,
            })
            merged_features.extend(result.get("features", []))
            merged_relationships.extend(result.get("relationships", []))
            merged_ownership.extend(result.get("ownership", []))

        return {
            "features": merged_features,
            "relationships": merged_relationships,
            "ownership": merged_ownership,
        }
