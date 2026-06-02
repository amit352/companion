from abc import abstractmethod
from typing import Any

from pydantic import BaseModel

from .plugin_base import PluginBase, PluginContext


class IntegrationCapability(BaseModel):
    can_push: bool = False
    can_pull: bool = False
    supports_webhooks: bool = False
    entity_types: list[str] = []


class IntegrationPlugin(PluginBase):
    """Plugin type 4.6: Bridges Companion with external systems (GitHub, Jira, Neo4j, etc.)."""

    @abstractmethod
    def capabilities(self) -> IntegrationCapability:
        """Declare what this integration can do."""

    @abstractmethod
    async def push(self, entity_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Push data to the external system."""

    @abstractmethod
    async def pull(self, entity_type: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Pull data from the external system."""

    async def execute(self, context: PluginContext, inputs: dict[str, Any]) -> dict[str, Any]:
        action = inputs["action"]
        if action == "push":
            return await self.push(inputs["entity_type"], inputs["data"])
        elif action == "pull":
            return {"results": await self.pull(inputs["entity_type"], inputs.get("filters", {}))}
        raise ValueError(f"Unknown action: {action}")
