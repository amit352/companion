import pytest
from feature_graph.sdk.registry import PluginRegistry
from feature_graph.sdk.base.plugin_base import PluginBase, PluginManifest, PluginType, PluginContext
from typing import Any


class DummyPlugin(PluginBase):
    async def execute(self, context: PluginContext, inputs: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True}


def make_plugin(name: str, plugin_type: PluginType) -> DummyPlugin:
    return DummyPlugin(PluginManifest(name=name, version="1.0.0", plugin_type=plugin_type))


def test_register_and_get():
    registry = PluginRegistry()
    plugin = make_plugin("test-parser", PluginType.PARSER)
    registry.register(plugin)
    assert registry.get("test-parser") is plugin


def test_get_by_type():
    registry = PluginRegistry()
    p1 = make_plugin("parser-1", PluginType.PARSER)
    p2 = make_plugin("parser-2", PluginType.PARSER)
    p3 = make_plugin("extractor-1", PluginType.FEATURE_EXTRACTOR)
    registry.register(p1)
    registry.register(p2)
    registry.register(p3)

    parsers = registry.get_by_type(PluginType.PARSER)
    assert len(parsers) == 2
    assert all(p.plugin_type == PluginType.PARSER for p in parsers)


def test_duplicate_registration_raises():
    registry = PluginRegistry()
    plugin = make_plugin("dup", PluginType.PARSER)
    registry.register(plugin)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(make_plugin("dup", PluginType.PARSER))


def test_count():
    registry = PluginRegistry()
    assert registry.count == 0
    registry.register(make_plugin("p1", PluginType.PARSER))
    assert registry.count == 1
