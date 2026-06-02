from collections import defaultdict

import structlog

from companion.sdk.base.plugin_base import PluginBase, PluginType

log = structlog.get_logger()


class PluginRegistry:
    """Thread-safe plugin registry. Plugins self-register here (FR-1)."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginBase] = {}
        self._by_type: dict[PluginType, list[PluginBase]] = defaultdict(list)

    def register(self, plugin: PluginBase) -> None:
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin '{plugin.name}' already registered")
        self._plugins[plugin.name] = plugin
        self._by_type[plugin.plugin_type].append(plugin)
        log.info("plugin_registered", name=plugin.name, type=plugin.plugin_type)

    def get(self, name: str) -> PluginBase | None:
        return self._plugins.get(name)

    def get_by_type(self, plugin_type: PluginType) -> list[PluginBase]:
        return list(self._by_type.get(plugin_type, []))

    def all(self) -> list[PluginBase]:
        return list(self._plugins.values())

    @property
    def count(self) -> int:
        return len(self._plugins)
