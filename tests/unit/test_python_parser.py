import importlib.util
import json
from pathlib import Path

import pytest
from feature_graph.sdk.base.plugin_base import PluginManifest


def load_python_plugin():
    manifest_path = Path("plugins/parsers/python_parser/plugin.json")
    data = json.loads(manifest_path.read_text())
    spec = importlib.util.spec_from_file_location("py_plugin", manifest_path.parent / "plugin.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Plugin(PluginManifest(**data))


@pytest.mark.asyncio
async def test_extracts_functions():
    plugin = load_python_plugin()
    result = await plugin.parse_file("auth.py", "def login(user, pwd): pass\ndef logout(): pass")
    names = [s.name for s in result.symbols]
    assert "login" in names
    assert "logout" in names


@pytest.mark.asyncio
async def test_extracts_classes():
    plugin = load_python_plugin()
    result = await plugin.parse_file("service.py", "class UserService:\n    pass")
    names = [s.name for s in result.symbols]
    assert "UserService" in names


@pytest.mark.asyncio
async def test_extracts_imports():
    plugin = load_python_plugin()
    src = "import os\nfrom pathlib import Path\nimport json"
    result = await plugin.parse_file("utils.py", src)
    targets = [d.target for d in result.dependencies]
    assert "os" in targets
    assert "pathlib" in targets


@pytest.mark.asyncio
async def test_language_is_python():
    plugin = load_python_plugin()
    result = await plugin.parse_file("foo.py", "x = 1")
    assert result.language == "python"


@pytest.mark.asyncio
async def test_empty_file():
    plugin = load_python_plugin()
    result = await plugin.parse_file("empty.py", "")
    assert result.symbols == []
    assert result.dependencies == []


@pytest.mark.asyncio
async def test_symbol_line_numbers():
    plugin = load_python_plugin()
    src = "x = 1\n\ndef my_func():\n    pass"
    result = await plugin.parse_file("lines.py", src)
    func = next((s for s in result.symbols if s.name == "my_func"), None)
    assert func is not None
    assert func.line == 3
