import os
import tempfile
from pathlib import Path

import pytest
from companion.core.agents.project_scanner import ProjectScanner


@pytest.fixture
def sample_repo(tmp_path):
    (tmp_path / "main.py").write_text("def hello(): pass")
    (tmp_path / "utils.py").write_text("x = 1")
    (tmp_path / "app.ts").write_text("const x = 1;")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.py").write_text("ignored")
    return tmp_path


@pytest.mark.asyncio
async def test_scan_finds_files(sample_repo):
    scanner = ProjectScanner(sample_repo)
    result = await scanner.scan()

    paths = [f["path"] for f in result["files"]]
    assert any("main.py" in p for p in paths)
    assert any("utils.py" in p for p in paths)
    assert any("app.ts" in p for p in paths)


@pytest.mark.asyncio
async def test_scan_ignores_node_modules(sample_repo):
    scanner = ProjectScanner(sample_repo)
    result = await scanner.scan()

    paths = [f["path"] for f in result["files"]]
    assert not any("node_modules" in p for p in paths)


@pytest.mark.asyncio
async def test_scan_language_detection(sample_repo):
    scanner = ProjectScanner(sample_repo)
    result = await scanner.scan()

    langs = {f["language"] for f in result["files"]}
    assert "python" in langs
    assert "typescript" in langs


@pytest.mark.asyncio
async def test_incremental_skips_unchanged(sample_repo):
    scanner = ProjectScanner(sample_repo)
    full = await scanner.scan(incremental=False)

    # second scan with no changes — incremental should return nothing
    incremental = await scanner.scan(incremental=True)
    assert len(incremental["files"]) == 0


@pytest.mark.asyncio
async def test_incremental_picks_up_new_file(sample_repo):
    scanner = ProjectScanner(sample_repo)
    await scanner.scan(incremental=False)

    (sample_repo / "new_file.py").write_text("y = 2")
    incremental = await scanner.scan(incremental=True)

    paths = [f["path"] for f in incremental["files"]]
    assert any("new_file.py" in p for p in paths)
