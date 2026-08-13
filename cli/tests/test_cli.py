"""End-to-end tests for the CLI: init, add, lock, verify, pull, show, lint."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from speccify_cli.__main__ import app
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
LIBRARY = REPO_ROOT / "skills"
MAIN = "@speccify/macos-notarize-tauri"
CHILD = "@speccify/apple-developer-id-cert"

runner = CliRunner()


@pytest.fixture
def project(tmp_path: Path) -> Path:
    result = runner.invoke(app, ["init", "--project", str(tmp_path)])
    assert result.exit_code == 0, result.output
    return tmp_path


def _add(project: Path, reference: str = MAIN):
    return runner.invoke(
        app, ["add", reference, "--project", str(project), "--library", str(LIBRARY)]
    )


def test_init_writes_a_minimal_manifest(project: Path) -> None:
    manifest = yaml.safe_load((project / "speccify.yaml").read_text(encoding="utf-8"))
    assert manifest == {"schema_version": 1}


def test_add_pins_the_playbook_and_its_child(project: Path) -> None:
    result = _add(project)
    assert result.exit_code == 0, result.output
    lockfile = yaml.safe_load((project / "speccify.lock").read_text(encoding="utf-8"))
    assert lockfile["schema_version"] == 1
    ids = [entry["id"] for entry in lockfile["playbooks"]]
    # The child comes along because a step delegates to it.
    assert ids == [CHILD, MAIN]
    assert all(entry["bundle_sha256"].startswith("sha256:") for entry in lockfile["playbooks"])


def test_verify_is_green_after_add(project: Path) -> None:
    _add(project)
    result = runner.invoke(app, ["verify", "--project", str(project), "--library", str(LIBRARY)])
    assert result.exit_code == 0, result.output
    assert "agree" in result.output


def test_verify_reports_bundle_drift(project: Path, tmp_path: Path) -> None:
    """A changed bundle must not pass verification."""
    library = tmp_path / "library"
    import shutil

    shutil.copytree(LIBRARY, library)
    assert (
        runner.invoke(
            app, ["add", MAIN, "--project", str(project), "--library", str(library)]
        ).exit_code
        == 0
    )
    skill = library / "macos-notarize-tauri" / "SKILL.md"
    skill.write_text(
        skill.read_text(encoding="utf-8") + "\n<!-- edited elsewhere -->\n", encoding="utf-8"
    )
    result = runner.invoke(app, ["verify", "--project", str(project), "--library", str(library)])
    assert result.exit_code == 1
    assert "bundle hash drift" in result.output


def test_pull_materialises_bundles_including_assets(project: Path) -> None:
    _add(project)
    out = project / "out"
    result = runner.invoke(
        app, ["pull", "--project", str(project), "--library", str(LIBRARY), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    # Flat by name, not `<scope>/<name>`: `<skills-root>/<name>/SKILL.md` is
    # what an agent looks up, and pull writes where it will be found.
    assert (out / "macos-notarize-tauri" / "SKILL.md").is_file()
    assert (out / "macos-notarize-tauri" / "assets" / "verify-signatures.sh").is_file()


def test_show_describes_a_skill_without_installing_it(tmp_path: Path) -> None:
    """`show` is for the moment before installing: what is this, do I want it?"""
    skills = REPO_ROOT / "skills"
    runner.invoke(app, ["init", "--project", str(tmp_path)])
    result = runner.invoke(
        app, ["show", MAIN, "--project", str(tmp_path), "--library", str(skills)]
    )
    assert result.exit_code == 0, result.output
    assert "5 step(s)" in result.output
    assert "builds on: @speccify/apple-developer-id-cert" in result.output
    assert "4 source(s)" in result.output


def test_show_as_json_carries_the_body(tmp_path: Path) -> None:
    skills = REPO_ROOT / "skills"
    runner.invoke(app, ["init", "--project", str(tmp_path)])
    result = runner.invoke(
        app,
        ["show", MAIN, "--json", "--project", str(tmp_path), "--library", str(skills)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["id"] == MAIN
    assert "hardened runtime" in payload["body"]
    assert payload["uses"] == ["@speccify/apple-developer-id-cert@^1.0"]


def test_show_works_without_a_manifest_when_pointed_at_a_library(tmp_path: Path) -> None:
    """Reading a skill is not a project operation.

    Most skills live in some repository that is not a Speccify project. If
    `--library` names one, requiring a `speccify.yaml` next to it would stop an
    agent from reading anything it had not first `add`ed.
    """
    result = runner.invoke(
        app, ["show", MAIN, "--project", str(tmp_path), "--library", str(REPO_ROOT / "skills")]
    )
    assert result.exit_code == 0, result.output
    assert MAIN in result.output


def test_show_without_manifest_or_library_names_both_ways_out(tmp_path: Path) -> None:
    result = runner.invoke(app, ["show", MAIN, "--project", str(tmp_path)])
    assert result.exit_code == 1
    assert "speccify init" in result.output and "--library" in result.output


def test_lint_accepts_the_reference_library() -> None:
    """Everything shipped in this repo must always validate."""
    result = runner.invoke(app, ["lint", str(LIBRARY)])
    assert result.exit_code == 0, result.output
    assert "skill(s) validated" in result.output
    assert "fail" not in result.output


def test_lint_reports_a_broken_skill(tmp_path: Path) -> None:
    bundle = tmp_path / "Broken-Name"
    bundle.mkdir()
    (bundle / "SKILL.md").write_text(
        "---\nname: Broken-Name\ndescription: Something. Use when something.\n---\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["lint", str(bundle)])
    assert result.exit_code == 1
    assert "fail" in result.output


def test_check_is_clean_for_the_reference_library() -> None:
    result = runner.invoke(app, ["check", str(LIBRARY)])
    assert result.exit_code == 0, result.output
    assert "0 error(s), 0 warning(s)" in result.output


def test_check_warns_about_stale_sources() -> None:
    result = runner.invoke(app, ["check", str(LIBRARY), "--stale-days", "0"])
    assert result.exit_code == 0, result.output
    # Warnings do not fail the run — only errors do.
    assert "warning(s)" in result.output


def test_check_fails_on_a_reference_the_agent_cannot_read(tmp_path: Path) -> None:
    """A dangling pointer is an error, not a style note — the agent will try it."""
    bundle = tmp_path / "broken"
    bundle.mkdir()
    (bundle / "SKILL.md").write_text(
        "---\nname: broken\ndescription: Something. Use when something.\n---\n\n"
        "See [the details](DETAILS.md).\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["check", str(bundle)])
    assert result.exit_code == 1
    assert "DETAILS.md" in result.output


def test_lint_and_check_accept_the_shipped_skills() -> None:
    """The skills in `skills/` are the product; they must never be broken."""
    skills = REPO_ROOT / "skills"
    lint = runner.invoke(app, ["lint", str(skills)])
    assert lint.exit_code == 0, lint.output
    assert "skill(s) validated" in lint.output

    # Offline: specification, best practice and source age — no network.
    check = runner.invoke(app, ["check", str(skills)])
    assert check.exit_code == 0, check.output
    assert "0 error(s)" in check.output


def test_the_local_loop_works_on_skills(tmp_path: Path) -> None:
    """init -> add -> lock -> pull -> verify, against `skills/`.

    This is M1 in one test: a project declares a skill, the child it builds on
    is resolved transitively, and both land where Claude Code looks for them —
    flat, by name, with assets.
    """
    skills = REPO_ROOT / "skills"
    assert runner.invoke(app, ["init", "--project", str(tmp_path)]).exit_code == 0

    added = runner.invoke(app, ["add", MAIN, "--project", str(tmp_path), "--library", str(skills)])
    assert added.exit_code == 0, added.output

    out = tmp_path / ".claude" / "skills"
    pulled = runner.invoke(
        app, ["pull", "--project", str(tmp_path), "--library", str(skills), "--out", str(out)]
    )
    assert pulled.exit_code == 0, pulled.output

    # The parent and the child it delegates to, both by bare name.
    assert (out / "macos-notarize-tauri" / "SKILL.md").is_file()
    assert (out / "apple-developer-id-cert" / "SKILL.md").is_file()
    assert (out / "macos-notarize-tauri" / "assets" / "verify-signatures.sh").is_file()

    verified = runner.invoke(app, ["verify", "--project", str(tmp_path), "--library", str(skills)])
    assert verified.exit_code == 0, verified.output
