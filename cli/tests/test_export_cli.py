"""End-to-end for `speccify export`: project skill → library → back into a project."""

from __future__ import annotations

from pathlib import Path

import yaml
from speccify_cli.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()

PROJECT_SKILL = """---
name: notarize
description: Notarizes a bundle. Use when shipping a .dmg.
---

## 1 — Sign

Run [verify](../../tools/verify/TOOL.md) on /Users/me/Work/App/build/App.app.

## Sources

- [Apple](https://developer.apple.com/notarization) — retrieved 2026-08-01

## In this project

- Team id ABCDE12345.
"""

TOOL_MD = """---
name: verify
description: Checks a bundle's signature.
inputs:
  type: object
  properties:
    bundle: {type: string}
  required: [bundle]
outputs:
  type: object
  properties:
    ok: {type: boolean}
  required: [ok]
---

## Examples

### signed bundle
input:  {"bundle": "fixtures/Signed.app"}
output: {"ok": true}
"""


def _project_with_skill(root: Path) -> Path:
    project = root / "project"
    (project / ".agent/skills/notarize").mkdir(parents=True)
    (project / ".agent/skills/notarize/SKILL.md").write_text(PROJECT_SKILL, encoding="utf-8")
    (project / ".agent/tools/verify/fixtures").mkdir(parents=True)
    (project / ".agent/tools/verify/TOOL.md").write_text(TOOL_MD, encoding="utf-8")
    (project / ".agent/tools/verify/macos.sh").write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    (project / ".agent/tools/verify/windows.ps1").write_text("Write-Output ok\n", encoding="utf-8")
    (project / ".agent/tools/verify/fixtures/Signed.app").write_bytes(b"")
    return project


def _library_with_scope(root: Path) -> Path:
    library = root / "library"
    (library / "skills/other").mkdir(parents=True)
    (library / "skills/other/SKILL.md").write_text(
        "---\nname: other\ndescription: Another skill.\nmetadata:\n  speccify.version: 1.0.0\n"
        "  speccify.scope: acme\n---\n\n## Do\n\nSomething.\n",
        encoding="utf-8",
    )
    return library


def test_export_writes_a_library_skill_and_reports_suspects(tmp_path: Path) -> None:
    project = _project_with_skill(tmp_path)
    library = _library_with_scope(tmp_path)

    result = runner.invoke(
        app,
        [
            "export",
            "notarize",
            "--to",
            str(library),
            "--project",
            str(project),
            "--platform",
            "macos",
        ],
    )
    assert result.exit_code == 0, result.output
    target = library / "skills/notarize"
    text = (target / "SKILL.md").read_text(encoding="utf-8")
    front = yaml.safe_load(text.split("---\n")[1])
    # Scope joins the library's namespace; version starts at 1.0.0.
    assert front["metadata"] == {"speccify.version": "1.0.0", "speccify.scope": "acme"}
    assert "## In this project" not in text
    assert "[verify](tools/verify/TOOL.md)" in text
    assert (target / "tools/verify/TOOL.md").read_text(encoding="utf-8") == TOOL_MD
    assert (target / "tools/verify/reference.sh").is_file()
    assert not (target / "tools/verify/windows.ps1").exists()
    assert (target / "tools/verify/fixtures/Signed.app").is_file()

    assert "@acme/notarize 1.0.0" in result.output
    assert "SKILL.md:" in result.output and "/Users/me/Work/App/build/App.app" in result.output
    assert f'speccify add @acme/notarize --source "{library.resolve()}"' in result.output

    # Second export refuses to overwrite unless forced; forced bumps the patch version.
    again = runner.invoke(
        app, ["export", "notarize", "--to", str(library), "--project", str(project)]
    )
    assert again.exit_code == 1
    assert "--force" in again.output
    forced = runner.invoke(
        app, ["export", "notarize", "--to", str(library), "--project", str(project), "--force"]
    )
    assert forced.exit_code == 0, forced.output
    assert "@acme/notarize 1.0.1" in forced.output


def test_exported_skill_round_trips_into_a_fresh_project(tmp_path: Path) -> None:
    project = _project_with_skill(tmp_path)
    library = _library_with_scope(tmp_path)
    exported = runner.invoke(
        app, ["export", "notarize", "--to", str(library), "--project", str(project)]
    )
    assert exported.exit_code == 0, exported.output

    fresh = tmp_path / "fresh"
    assert runner.invoke(app, ["init", "--project", str(fresh)]).exit_code == 0
    added = runner.invoke(
        app, ["add", "@acme/notarize", "--project", str(fresh), "--library", str(library)]
    )
    assert added.exit_code == 0, added.output
    expanded = runner.invoke(
        app,
        [
            "expand",
            "notarize",
            "--project",
            str(fresh),
            "--library",
            str(library),
            "--platform",
            "macos",
        ],
    )
    assert expanded.exit_code == 0, expanded.output
    skill = (fresh / ".agent/skills/notarize/SKILL.md").read_text(encoding="utf-8")
    assert "## In this project" in skill
    assert "Team id" not in skill  # the old project's section did not travel
    assert (fresh / ".agent/tools/verify/TOOL.md").is_file()
    assert (fresh / ".agent/tools/verify/reference.sh").is_file()
    # The reference is a hint, not an implementation: macos.sh is still to do.
    assert "verify" in expanded.output


def test_export_without_any_scope_says_so(tmp_path: Path) -> None:
    project = _project_with_skill(tmp_path)
    library = tmp_path / "empty-library"
    library.mkdir()
    result = runner.invoke(
        app, ["export", "notarize", "--to", str(library), "--project", str(project)]
    )
    assert result.exit_code == 0, result.output
    assert "No scope" in result.output
    text = (library / "skills/notarize/SKILL.md").read_text(encoding="utf-8")
    assert "speccify.scope" not in text
