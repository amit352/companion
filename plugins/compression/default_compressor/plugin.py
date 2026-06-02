"""
Default AI Compression plugin.
Target: 500K token raw repo → ~3K token compressed context (Section 10, goal: 70% reduction).

Strategy:
  1. Feature clustering — group related features
  2. Dependency summarization — reduce edge list to essential paths
  3. Semantic deduplication — collapse near-identical features
  4. Claude-powered abstraction — generate plain-English summaries
"""
import json
from typing import Any

import anthropic

from companion.sdk.base.compression_plugin import CompressedContext, CompressionPlugin
from companion.sdk.base.plugin_base import PluginManifest

_COMPRESSION_SYSTEM = """You are an AI context compression specialist.
Given a feature graph from a codebase, generate a maximally compressed but information-dense summary.

Rules:
- Group related features into semantic clusters
- For each cluster, write a 1-2 sentence summary
- Preserve all dependency relationships as compact edge list
- Target 3,000 tokens total output maximum

Return valid JSON:
{
  "semantic_clusters": [
    {"cluster_name": "str", "features": ["names"], "summary": "str"}
  ],
  "feature_summaries": [
    {"name": "str", "one_liner": "str", "depends_on": ["names"]}
  ],
  "dependency_summaries": [
    {"from": "str", "to": "str", "kind": "str"}
  ],
  "runtime_summaries": []
}"""


class Plugin(CompressionPlugin):
    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(manifest)
        self._client = anthropic.Anthropic()

    async def compress(
        self,
        companion: dict[str, Any],
        query_context: str | None = None,
    ) -> CompressedContext:
        features = companion.get("features", [])
        relationships = companion.get("relationships", [])

        raw_json = json.dumps({"features": features, "relationships": relationships})
        raw_token_estimate = len(raw_json.split()) * 4 // 3  # rough estimate

        user_msg = raw_json
        if query_context:
            user_msg = f"Query focus: {query_context}\n\n{raw_json}"

        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",  # use Haiku — cheaper for compression
            max_tokens=3000,
            system=_COMPRESSION_SYSTEM,
            messages=[{"role": "user", "content": user_msg[:50_000]}],  # hard token cap
        )

        data = json.loads(response.content[0].text)
        compressed_json = json.dumps(data)
        compressed_token_estimate = len(compressed_json.split()) * 4 // 3
        ratio = 1.0 - (compressed_token_estimate / max(raw_token_estimate, 1))

        return CompressedContext(
            feature_summaries=data.get("feature_summaries", []),
            dependency_summaries=data.get("dependency_summaries", []),
            runtime_summaries=data.get("runtime_summaries", []),
            raw_token_estimate=raw_token_estimate,
            compressed_token_estimate=compressed_token_estimate,
            compression_ratio=round(ratio, 3),
            semantic_clusters=data.get("semantic_clusters", []),
        )
