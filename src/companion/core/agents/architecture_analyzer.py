"""Agent 4: Assign architectural layers to features and services."""
from typing import Any

import structlog

log = structlog.get_logger()

_LAYER_KEYWORDS: dict[str, list[str]] = {
    "api": ["router", "controller", "handler", "endpoint", "view", "route"],
    "service": ["service", "manager", "processor", "orchestrator", "usecase"],
    "data": ["repository", "dao", "model", "schema", "migration", "table"],
    "ui": ["component", "page", "screen", "widget", "layout", "template"],
    "utility": ["util", "helper", "lib", "common", "shared", "base"],
    "config": ["config", "settings", "env", "constant"],
}


class ArchitectureAnalyzer:
    async def analyze(
        self,
        features: dict[str, Any],
        parse_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        layer_assignments: dict[str, str] = {}
        layers: dict[str, list[str]] = {k: [] for k in _LAYER_KEYWORDS}

        for result in parse_results:
            file_path = result.get("file", "").lower()
            layer = self._classify_file(file_path)
            for symbol in result.get("symbols", []):
                sym_layer = self._classify_file(symbol.get("name", "").lower()) or layer
                layer_assignments[symbol.get("name", "")] = sym_layer
                if sym_layer:
                    layers[sym_layer].append(symbol.get("name", ""))

        for feature in features.get("features", []):
            name = feature.get("name", "").lower()
            if "auth" in name or "login" in name:
                feature["layer"] = "service"
            elif "api" in name or "endpoint" in name:
                feature["layer"] = "api"
            elif "table" in name or "db" in name:
                feature["layer"] = "data"
            else:
                feature["layer"] = "service"

        return {"layers": layers, "assignments": layer_assignments}

    def _classify_file(self, path: str) -> str:
        for layer, keywords in _LAYER_KEYWORDS.items():
            if any(kw in path for kw in keywords):
                return layer
        return "utility"
