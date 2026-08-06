"""Tests for the MCP tools — thin adapters, so the checks stay behavioural."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from speccify_mcp.tools import (
    run_lock,
    run_playbook_get,
    run_playbook_list,
    run_playbook_step,
    run_pull,
    run_verify,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN = "@speccify/macos-notarize-tauri"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project with its own copy of the playbook library."""
    shutil.copytree(REPO_ROOT / "playbooks", tmp_path / "playbooks")
    (tmp_path / "speccify.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    return tmp_path


def test_playbook_list_describes_the_library(project: Path) -> None:
    result = run_playbook_list(project)
    assert result.ok, result.message
    titles = {entry["id"]: entry for entry in result.playbooks}
    assert MAIN in titles
    assert titles[MAIN]["steps"] == 5
    assert "notarization" in titles[MAIN]["keywords"]


def test_playbook_get_resolves_sources_per_step(project: Path) -> None:
    result = run_playbook_get(project, reference=MAIN)
    assert result.ok, result.message
    steps = result.playbook["steps"]
    assert [step["id"] for step in steps][0] == "signing_identity"
    notarize = next(step for step in steps if step["id"] == "notarize")
    assert notarize["sources"][0]["retrieved"] == "2026-08-06"
    assert result.playbook["assets"] == ["assets/verify-signatures.sh"]


def test_playbook_step_returns_one_step(project: Path) -> None:
    result = run_playbook_step(project, reference=MAIN, step_id="staple")
    assert result.ok, result.message
    assert result.playbook["step"]["verify"].startswith("`spctl --assess`")


def test_unknown_reference_is_structured(project: Path) -> None:
    result = run_playbook_get(project, reference="@org/nope")
    assert not result.ok
    assert result.code == "not_found"


def test_lock_pull_verify_round_trip(project: Path) -> None:
    (project / "speccify.yaml").write_text(
        f"schema_version: 1\ndependencies:\n  '{MAIN}': ^1.0\n", encoding="utf-8"
    )
    locked = run_lock(project)
    assert locked.ok, locked.message
    assert len(locked.entries) == 2

    pulled = run_pull(project, out_dir=Path("out"))
    assert pulled.ok, pulled.message
    assert any("verify-signatures.sh" in path for path in pulled.files)

    verified = run_verify(project)
    assert verified.ok, verified.problems


def test_verify_reports_drift_as_a_result(project: Path) -> None:
    (project / "speccify.yaml").write_text(
        f"schema_version: 1\ndependencies:\n  '{MAIN}': ^1.0\n", encoding="utf-8"
    )
    run_lock(project)
    playbook = (
        project / "playbooks" / "speccify" / "macos-notarize-tauri" / "1.0.0" / "playbook.yaml"
    )
    playbook.write_text(playbook.read_text(encoding="utf-8") + "\n# touched\n", encoding="utf-8")
    verified = run_verify(project)
    assert not verified.ok
    assert any("bundle hash drift" in problem for problem in verified.problems)
