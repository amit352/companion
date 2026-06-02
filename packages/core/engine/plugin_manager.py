import importlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import structlog

from feature_graph.sdk.base.plugin_base import PluginBase, PluginManifest, PluginType
from feature_graph.sdk.registry import PluginRegistry

log = structlog.get_logger()


class PluginManager:
    """Discovers, loads, and manages plugin lifecycle."""

    def __init__(self, plugin_dirs: list[Path], registry: PluginRegistry) -> None:
        self._plugin_dirs = plugin_dirs
        self._registry = registry
        self._loaded: dict[str, PluginBase] = {}

    async def discover_and_load(self) -> None:
        """Auto-discover plugins from all configured directories (FR-2)."""
        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue
            for manifest_path in plugin_dir.rglob("plugin.json"):
                await self._load_plugin(manifest_path)

    async def _load_plugin(self, manifest_path: Path) -> None:
        try:
            manifest = PluginManifest(**json.loads(manifest_path.read_text()))
            entrypoint = manifest_path.parent / manifest.entrypoint

            spec = importlib.util.spec_from_file_location(manifest.name, entrypoint)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load {entrypoint}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[attr-defined]

            plugin_cls = getattr(module, "Plugin", None)
            if plugin_cls is None:
                raise AttributeError(f"{entrypoint} must expose a top-level 'Plugin' class")

            plugin: PluginBase = plugin_cls(manifest)
            await plugin.initialize()

            self._registry.register(plugin)
            self._loaded[manifest.name] = plugin
            log.info("plugin_loaded", name=manifest.name, type=manifest.plugin_type)

        except Exception as exc:
            log.error("plugin_load_failed", manifest=str(manifest_path), error=str(exc))

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[PluginBase]:
        return self._registry.get_by_type(plugin_type)

    async def shutdown_all(self) -> None:
        for plugin in self._loaded.values():
            await plugin.teardown()
        log.info("all_plugins_shutdown", count=len(self._loaded))

    @property
    def loaded_count(self) -> int:
        return len(self._loaded)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {"name": p.manifest.name, "version": p.manifest.version, "type": p.manifest.plugin_type}
            for p in self._loaded.values()
        ]
