from abc import abstractmethod
from typing import Any

from pydantic import BaseModel

from .plugin_base import PluginBase, PluginContext


class FeatureNode(BaseModel):
    id: str
    name: str
    description: str
    domain: str
    confidence: float  # 0.0–1.0
    source_files: list[str]
    tags: list[str] = []


class FeatureRelationship(BaseModel):
    source_id: str
    target_id: str
    kind: str  # depends_on | uses | extends | conflicts_with
    weight: float = 1.0


class FeatureOwnership(BaseModel):
    feature_id: str
    team: str | None = None
    authors: list[str] = []
    primary_file: str | None = None


class FeatureExtractionOutput(BaseModel):
    features: list[FeatureNode]
    relationships: list[FeatureRelationship]
    ownership: list[FeatureOwnership]


class FeaturePlugin(PluginBase):
    """
    Plugin type 4.2: Identifies business features from source code.
    LLM-powered — uses Claude to interpret semantic meaning from AST + source.
    """

    @abstractmethod
    async def extract_features(
        self,
        symbols: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
        source_context: str,
    ) -> FeatureExtractionOutput:
        """Identify business-level features from parsed code structures."""

    async def execute(self, context: PluginContext, inputs: dict[str, Any]) -> dict[str, Any]:
        result = await self.extract_features(
            symbols=inputs.get("symbols", []),
            dependencies=inputs.get("dependencies", []),
            source_context=inputs.get("source_context", ""),
        )
        return result.model_dump()
