"""Authentication / authorization feature detector."""
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
    "login", "logout", "authenticate", "authorize", "token", "session",
    "password", "oauth", "jwt", "credential", "permission", "role",
    "user", "account", "signup", "register", "mfa", "2fa", "sso",
    "refresh", "access", "identity", "principal", "claim", "scope",
}

_SYSTEM = build_system_prompt(
    domain="authentication and authorization",
    extra_instructions=(
        "Focus on: login/logout flows, OAuth/OIDC integrations, session management, "
        "JWT handling, role-based access control, MFA, and SSO. "
        "Only include features backed by at least one matching symbol."
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
