"""
Shared utilities for LLM-based feature extractor plugins.
All extractors follow the same pattern:
  1. Filter symbols by domain keywords (cheap, local)
  2. Send filtered symbols to Claude with a domain-specific system prompt
  3. Parse and validate the JSON response
  4. Return FeatureExtractionOutput
"""
import json
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
