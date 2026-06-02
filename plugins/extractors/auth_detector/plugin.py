"""
Built-in Authentication Feature Detector.
Uses Claude to identify auth-related business features from parsed symbols.
"""
import json
from typing import Any

import anthropic

from feature_graph.sdk.base.feature_plugin import (
    FeatureExtractionOutput, FeatureNode, FeatureOwnership, FeaturePlugin, FeatureRelationship,
)
from feature_graph.sdk.base.plugin_base import PluginManifest

_AUTH_KEYWORDS = {
    "login", "logout", "authenticate", "authorize", "token", "session",
    "password", "oauth", "jwt", "credential", "permission", "role",
    "user", "account", "signup", "register", "mfa", "2fa", "sso",
}

_SYSTEM_PROMPT = """You are a code intelligence expert. Given a list of code symbols and dependencies,
identify authentication and authorization related business features.

Return a JSON object with this exact shape:
{
  "features": [
    {
      "name": "string — concise feature name",
      "description": "string — what business capability this represents",
      "domain": "auth",
      "confidence": 0.0-1.0,
      "source_files": ["list of file paths"],
      "tags": ["list of relevant tags"]
    }
  ],
  "relationships": [
    {"source_id": "feature name", "target_id": "feature name", "kind": "depends_on|uses"}
  ],
  "ownership": []
}

Only include features with confidence >= 0.6. Return valid JSON only."""


class Plugin(FeaturePlugin):
    def __init__(self, manifest: PluginManifest) -> None:
        super().__init__(manifest)
        self._client = anthropic.Anthropic()

    async def extract_features(
        self,
        symbols: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
        source_context: str,
    ) -> FeatureExtractionOutput:
        # Filter to auth-related symbols first to reduce tokens
        auth_symbols = [
            s for s in symbols
            if any(kw in s.get("name", "").lower() for kw in _AUTH_KEYWORDS)
        ]

        if not auth_symbols:
            return FeatureExtractionOutput(features=[], relationships=[], ownership=[])

        user_content = json.dumps({
            "context": source_context,
            "symbols": auth_symbols[:100],  # cap at 100 for token budget
            "dependencies": [
                d for d in dependencies
                if any(kw in d.get("target", "").lower() for kw in _AUTH_KEYWORDS)
            ][:50],
        })

        response = self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = response.content[0].text
        data = json.loads(raw)

        features = [FeatureNode(**f) for f in data.get("features", [])]
        relationships = [FeatureRelationship(**r) for r in data.get("relationships", [])]
        ownership = [FeatureOwnership(**o) for o in data.get("ownership", [])]

        return FeatureExtractionOutput(
            features=features,
            relationships=relationships,
            ownership=ownership,
        )
