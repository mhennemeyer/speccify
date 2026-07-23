"""Tests für das MCP-Tool `mock` (P2 Stage 5)."""

from __future__ import annotations

from pathlib import Path

from speccify_mcp.tools import run_mock

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_run_mock_writes_closure_and_reports_pin(tmp_path: Path) -> None:
    result = run_mock(
        project_root=REPO_ROOT,
        spec_ref="@org/search-bar",
        out_dir=tmp_path / "mocks",
    )
    payload = result.to_dict()
    assert payload["ok"] is True, payload["message"]
    assert payload["files"] == [
        "org/Button.mock.tsx",
        "org/SearchBar.mock.tsx",
        "org/TextInput.mock.tsx",
    ]
    assert payload["template_set"] == "p2-mock-react"
    assert (tmp_path / "mocks" / "org" / "SearchBar.mock.tsx").is_file()


def test_run_mock_reports_mock_failed_for_unknown_spec(tmp_path: Path) -> None:
    result = run_mock(
        project_root=REPO_ROOT,
        spec_ref="@org/does-not-exist",
        out_dir=tmp_path / "mocks",
    )
    assert result.ok is False
    assert result.code == "mock_failed"


def test_run_mock_relative_out_dir_is_project_rooted(tmp_path: Path) -> None:
    # Projekt-Root = tmp_path mit eigener Registry-Kopie → out landet darunter.
    import shutil

    shutil.copytree(REPO_ROOT / "registry-fixtures", tmp_path / "registry-fixtures")
    result = run_mock(
        project_root=tmp_path,
        spec_ref="@org/button@0.1.0",
        out_dir=Path("./speccify_mocks"),
    )
    assert result.ok is True
    assert (tmp_path / "speccify_mocks" / "org" / "Button.mock.tsx").is_file()
