"""Tests für das MCP-Tool `build` (Phase P4 Stufe 3)."""

from __future__ import annotations

import shutil
from pathlib import Path

from speccify_mcp.tools import run_build

REPO_ROOT = Path(__file__).resolve().parents[2]


def _project(tmp_path: Path) -> Path:
    """Wegwerf-Projekt mit einer Kopie der Registry-Fixtures."""
    shutil.copytree(REPO_ROOT / "registry-fixtures", tmp_path / "registry-fixtures")
    return tmp_path


def test_build_writes_the_project_relative_to_the_project_root(tmp_path: Path) -> None:
    root = _project(tmp_path)
    result = run_build(root, spec_ref="@org/demo-app", out_dir=Path("./app"))
    assert result.ok, result.message
    assert result.template_set == "p4-app-react"
    assert result.mocks is True
    assert (root / "app" / "src" / "App.tsx").exists()
    assert "src/components/org/SearchBar.mock.tsx" in result.files


def test_build_reports_non_app_specs_as_structured_failure(tmp_path: Path) -> None:
    root = _project(tmp_path)
    result = run_build(root, spec_ref="@org/button", out_dir=Path("./app"))
    assert not result.ok
    assert result.code == "build_failed"
    assert "erwartet `kind: app`" in result.message


def test_build_reports_unknown_spec_as_structured_failure(tmp_path: Path) -> None:
    root = _project(tmp_path)
    result = run_build(root, spec_ref="@org/nope", out_dir=Path("./app"))
    assert not result.ok
    assert result.code == "build_failed"


def test_build_reports_cache_miss_without_mocks(tmp_path: Path) -> None:
    """Ohne Mocks und ohne passenden Cache-Eintrag ist `cache_miss` die Antwort."""
    root = _project(tmp_path)
    result = run_build(
        root,
        spec_ref="@org/demo-app",
        out_dir=Path("./app"),
        mocks=False,
        cache_dir=Path("./leerer-cache"),
    )
    assert not result.ok
    assert result.code == "cache_miss"


def test_build_matches_the_cli_bytes(tmp_path: Path) -> None:
    from speccify_cli.commands.build import run_build as cli_run_build

    root = _project(tmp_path)
    mcp_result = run_build(root, spec_ref="@org/demo-app", out_dir=Path("./app"))
    cli_result = cli_run_build(
        "@org/demo-app",
        registry_path=root / "registry-fixtures",
        out_dir=None,
    )
    assert mcp_result.files == sorted(cli_result.files)
    for rel_path, data in cli_result.files.items():
        assert (root / "app" / rel_path).read_bytes() == data, rel_path
