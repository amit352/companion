"""Business workflow / process / state machine feature detector."""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parents[1]))

from _base import (
    build_system_prompt, call_claude, filter_deps, filter_symbols, parse_output,
)
from companion.sdk.base.feature_plugin import FeatureExtractionOutput, FeaturePlugin
from companion.sdk.base.plugin_base import PluginManifest

_KEYWORDS = {
    "workflow", "process", "pipeline", "step", "stage", "state", "transition",
    "job", "task", "queue", "worker", "handler", "scheduler", "event",
    "approval", "review", "publish", "draft", "submit", "complete", "cancel",
    "trigger", "hook", "callback", "listener", "observer", "saga",
}

_SYSTEM = build_system_prompt(
    domain="business workflows and processes",
    extra_instructions=(
        "Focus on: multi-step processes, state machines, job queues, approval flows, "
        "event-driven pipelines, and background task orchestration. "
        "Each feature should represent a distinct business process or workflow."
    ),
)


class Plugin(FeaturePlugin):
    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(manifest)

    async def extract_features(
        self,
        symbols: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
        source_context: str,
    ) -> FeatureExtractionOutput:
        filtered_symbols = filter_symbols(symbols, _KEYWORDS)
        if not filtered_symbols:
            return FeatureExtractionOutput(features=[], relationships=[], ownership=[])

        data = call_claude(_SYSTEM, {
            "context": source_context,
            "symbols": filtered_symbols,
            "dependencies": filter_deps(dependencies, _KEYWORDS),
        })
        return parse_output(data)
