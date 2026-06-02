from abc import abstractmethod
from typing import Any

from pydantic import BaseModel

from .plugin_base import PluginBase, PluginContext


class TraceSpan(BaseModel):
    trace_id: str
    span_id: str
    operation: str
    service: str
    duration_ms: float
    status: str
    tags: dict[str, Any] = {}


class RuntimeGraph(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    bottlenecks: list[dict[str, Any]]


class RuntimePlugin(PluginBase):
    """
    Plugin type 4.5: Analyzes runtime behavior via OpenTelemetry / Jaeger / Zipkin traces.
    Maps runtime service calls back to feature graph nodes.
    """

    @abstractmethod
    async def analyze_traces(self, traces: list[TraceSpan]) -> RuntimeGraph:
        """Build a runtime dependency graph from collected traces."""

    async def execute(self, context: PluginContext, inputs: dict[str, Any]) -> dict[str, Any]:
        traces = [TraceSpan(**t) for t in inputs.get("traces", [])]
        result = await self.analyze_traces(traces)
        return result.model_dump()
