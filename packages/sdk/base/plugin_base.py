from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class PluginType(StrEnum):
    PARSER = "parser"
    FEATURE_EXTRACTOR = "feature-extractor"
    DOCUMENTATION = "documentation"
    AI_COMPRESSION = "ai-compression"
    RUNTIME_ANALYSIS = "runtime-analysis"
    INTEGRATION = "integration"


class PluginManifest(BaseModel):
    name: str
    version: str
    plugin_type: PluginType
    languages: list[str] = []
    entrypoint: str = "./plugin.py"
    permissions: list[str] = []
    description: str = ""


class PluginContext(BaseModel):
    """Scoped context passed to every plugin execution — no raw engine access (NFR-4)."""

    repo_path: str
    graph_session_id: str
    config: dict[str, Any] = {}


class PluginBase(ABC):
    """Abstract base for all FeatureGraph plugins."""

    def __init__(self, manifest: PluginManifest) -> None:
        self.manifest = manifest

    async def initialize(self) -> None:
        """Called once after loading. Override to set up connections."""

    async def teardown(self) -> None:
        """Called on shutdown. Override to clean up resources."""

    @abstractmethod
    async def execute(self, context: PluginContext, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Main plugin entry point.
        Returns a dict of outputs defined by each plugin type contract.
        """

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def plugin_type(self) -> PluginType:
        return self.manifest.plugin_type
