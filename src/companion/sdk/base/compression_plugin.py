from abc import abstractmethod
from typing import Any

from pydantic import BaseModel

from .plugin_base import PluginBase, PluginContext


class CompressedContext(BaseModel):
    """AI-ready compressed representation. Target: 500K raw tokens → ~3K tokens (Section 10)."""

    feature_summaries: list[dict[str, Any]]
    dependency_summaries: list[dict[str, Any]]
    runtime_summaries: list[dict[str, Any]]
    raw_token_estimate: int
    compressed_token_estimate: int
    compression_ratio: float
    semantic_clusters: list[dict[str, Any]] = []


class CompressionPlugin(PluginBase):
    """
    Plugin type 4.4: Reduces token usage for AI systems.
    Implements clustering + summarization strategies (Section 10).
    """

    @abstractmethod
    async def compress(
        self,
        companion: dict[str, Any],
        query_context: str | None = None,
    ) -> CompressedContext:
        """
        Compress the full feature graph into an AI-ready context.
        query_context optionally biases compression toward relevant features.
        """

    async def execute(self, context: PluginContext, inputs: dict[str, Any]) -> dict[str, Any]:
        result = await self.compress(
            companion=inputs["companion"],
            query_context=inputs.get("query_context"),
        )
        return result.model_dump()
