"""Billing / payments / subscriptions feature detector."""
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parents[2]))

from _base import (
    build_system_prompt, call_claude, filter_deps, filter_symbols, parse_output,
)
from feature_graph.sdk.base.feature_plugin import FeatureExtractionOutput, FeaturePlugin
from feature_graph.sdk.base.plugin_base import PluginManifest

_KEYWORDS = {
    "payment", "billing", "invoice", "subscription", "plan", "price", "pricing",
    "charge", "stripe", "paypal", "checkout", "cart", "order", "refund", "coupon",
    "discount", "tier", "upgrade", "downgrade", "trial", "credit", "debit",
}

_SYSTEM = build_system_prompt(
    domain="billing and payments",
    extra_instructions=(
        "Focus on: payment processing, subscription lifecycle, invoicing, "
        "pricing tiers, refunds, and payment gateway integrations."
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
