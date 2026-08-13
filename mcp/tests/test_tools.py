"""Tests for the MCP tools — thin adapters, so the checks stay behavioural."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from speccify_mcp.tools import (
    run_lock,
    run_pull,
    run_skill_asset,
    run_skill_get,
    run_skill_list,
    run_verify,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN = "@speccify/macos-notarize-tauri"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project with its own copy of the skill library."""
    shutil.copytree(REPO_ROOT / "skills", tmp_path / "skills")
    (tmp_path / "speccify.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    return tmp_path


def test_skill_list_describes_the_library(project: Path) -> None:
    """Shallow on purpose: name, description, axes — not the bodies."""
    result = run_skill_list(project)
    assert result.ok, result.message
    entries = {entry["id"]: entry for entry in result.playbooks}
    assert MAIN in entries
    assert "tauri" in entries[MAIN]["stack"]
    assert "notarization" in entries[MAIN]["description"].lower()
    assert "body" not in entries[MAIN], "listing must not carry the instructions"


def test_skill_get_carries_the_body_and_its_sources(project: Path) -> None:
    """`get` is for a skill that is *not* installed — so it leads with the body."""
    result = run_skill_get(project, reference=MAIN)
    assert result.ok, result.message
    skill = result.playbook

    assert "hardened runtime" in skill["body"]
    assert [step["number"] for step in skill["steps"]] == [1, 2, 3, 4, 5]
    assert all(source["retrieved"] == "2026-08-06" for source in skill["sources"])
    assert skill["files"] == ["assets/verify-signatures.sh"]


def test_unknown_reference_is_structured(project: Path) -> None:
    result = run_skill_get(project, reference="@org/nope")
    assert not result.ok
    assert result.code == "not_found"


def test_lock_pull_verify_round_trip(project: Path) -> None:
    (project / "speccify.yaml").write_text(
        f"schema_version: 1\ndependencies:\n  '{MAIN}': ^1.0\n",
        encoding="utf-8",
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
        f"schema_version: 1\ndependencies:\n  '{MAIN}': ^1.0\n",
        encoding="utf-8",
    )
    run_lock(project)
    playbook = project / "skills" / "macos-notarize-tauri" / "SKILL.md"
    playbook.write_text(playbook.read_text(encoding="utf-8") + "\n# touched\n", encoding="utf-8")
    verified = run_verify(project)
    assert not verified.ok
    assert any("bundle hash drift" in problem for problem in verified.problems)


def test_playbook_asset_returns_the_script(project: Path) -> None:
    from speccify_mcp.tools import run_skill_asset

    result = run_skill_asset(project, reference=MAIN, path="assets/verify-signatures.sh")
    assert result.ok, result.message
    assert result.encoding == "utf-8"
    assert "codesign --verify" in result.content


def test_playbook_asset_lists_what_is_available(project: Path) -> None:
    from speccify_mcp.tools import run_skill_asset

    result = run_skill_asset(project, reference=MAIN, path="assets/nope")
    assert not result.ok
    assert "verify-signatures.sh" in result.message


def test_playbook_check_reports_health(project: Path) -> None:
    from speccify_mcp.tools import run_skill_check

    result = run_skill_check(project, reference=MAIN)
    assert result.ok, result.findings
    assert result.findings == []


def test_an_agent_can_find_and_read_a_skill_over_mcp(project: Path) -> None:
    """The path that matters, pinned so it cannot drift.

    list -> pick by stack -> get (body included) -> follow the child it builds
    on -> read a bundled file. No step tool: an installed skill is read from
    disk, and every tool definition costs context in every session.
    """
    listed = run_skill_list(project)
    assert listed.ok
    chosen = next(entry for entry in listed.playbooks if "tauri" in entry["stack"])

    whole = run_skill_get(project, reference=chosen["id"])
    assert whole.ok
    assert whole.playbook["body"].strip(), "the body is what the agent follows"

    # It builds on another skill, and that one resolves too.
    (child,) = whole.playbook["uses"]
    resolved = run_skill_get(project, reference=child)
    assert resolved.ok, resolved.message

    asset = run_skill_asset(project, reference=chosen["id"], path="assets/verify-signatures.sh")
    assert asset.ok and "codesign" in (asset.content or "")
