"""
Shared utilities for LLM-based feature extractor plugins.

Two backends:
  direct     — call Anthropic API with ANTHROPIC_API_KEY (standalone mode)
  claude-code — skip; features are ingested via /fg-analyze Claude Code skill instead
"""
import json
import os
from typing import Any

import anthropic

from companion.sdk.base.feature_plugin import (
    FeatureExtractionOutput,
    FeatureNode,
    FeatureOwnership,
    FeatureRelationship,
)

_RESPONSE_SCHEMA = """{
  "features": [
    {
      "name": "string",
      "description": "string",
      "domain": "string",
      "confidence": 0.0-1.0,
      "source_files": ["string"],
      "tags": ["string"]
    }
  ],
  "relationships": [
    {"source_id": "feature name", "target_id": "feature name", "kind": "depends_on|uses|extends"}
  ],
  "ownership": []
}"""


def build_system_prompt(domain: str, extra_instructions: str = "") -> str:
    return f"""You are a code intelligence expert specialising in {domain} features.
Given a list of code symbols and imports, identify {domain}-related business features.
Only include features with confidence >= 0.6.
{extra_instructions}
Return ONLY valid JSON matching this schema exactly:
{_RESPONSE_SCHEMA}"""


def filter_symbols(
    symbols: list[dict[str, Any]],
    keywords: set[str],
    max_symbols: int = 150,
) -> list[dict[str, Any]]:
    matched = [s for s in symbols if any(kw in s.get("name", "").lower() for kw in keywords)]
    return matched[:max_symbols]


def filter_deps(
    dependencies: list[dict[str, Any]],
    keywords: set[str],
    max_deps: int = 50,
) -> list[dict[str, Any]]:
    return [d for d in dependencies if any(kw in d.get("target", "").lower() for kw in keywords)][:max_deps]


def call_claude(system: str, payload: dict[str, Any], model: str = "claude-haiku-4-5-20251001") -> dict[str, Any]:
    if os.environ.get("LLM_BACKEND", "direct") == "claude-code":
        # In claude-code mode extraction is handled by the /fg-analyze skill.
        # The plugin pipeline still runs (for parsing) but LLM calls are no-ops.
        return {"features": [], "relationships": [], "ownership": []}

    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": json.dumps(payload)[:40_000]}],
        )
        return json.loads(response.content[0].text)
    except anthropic.APIStatusError as e:
        import structlog
        structlog.get_logger().warning("claude_api_error", status=e.status_code, message=str(e.message))
        return {"features": [], "relationships": [], "ownership": []}
    except Exception as e:
        import structlog
        structlog.get_logger().warning("claude_call_failed", error=str(e))
        return {"features": [], "relationships": [], "ownership": []}


def parse_output(data: dict[str, Any]) -> FeatureExtractionOutput:
    return FeatureExtractionOutput(
        features=[FeatureNode(**f) for f in data.get("features", [])],
        relationships=[FeatureRelationship(**r) for r in data.get("relationships", [])],
        ownership=[FeatureOwnership(**o) for o in data.get("ownership", [])],
    )
