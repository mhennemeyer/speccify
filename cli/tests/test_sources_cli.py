"""`speccify add --source`: the source is remembered, later commands need no --library."""

from __future__ import annotations

from pathlib import Path

import yaml
from speccify_cli.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()

SKILL = """---
name: notarize
description: Notarizes a bundle. Use when shipping a .dmg.
metadata:
  speccify.version: 1.2.0
  speccify.scope: acme
---

## 1 — Sign

Sign it.
"""


def _source(root: Path) -> Path:
    library = root / "checkout"
    (library / "skills/mac/notarize").mkdir(parents=True)
    (library / "skills/mac/notarize/SKILL.md").write_text(SKILL, encoding="utf-8")
    return library


def test_add_with_source_records_it_and_later_commands_find_the_skill(tmp_path: Path) -> None:
    source = _source(tmp_path)
    project = tmp_path / "project"
    assert runner.invoke(app, ["init", "--project", str(project)]).exit_code == 0

    added = runner.invoke(
        app, ["add", "@acme/notarize", "--project", str(project), "--source", str(source)]
    )
    assert added.exit_code == 0, added.output
    manifest = yaml.safe_load((project / "speccify.yaml").read_text(encoding="utf-8"))
    assert manifest["sources"] == [str(source)]
    assert manifest["dependencies"] == {"@acme/notarize": "^1.2"}
    lock = yaml.safe_load((project / "speccify.lock").read_text(encoding="utf-8"))
    # Provenance is the source location, not a bare "local".
    assert lock["playbooks"][0]["resolved_via"] == str(source)

    # No --library anywhere from here on.
    assert runner.invoke(app, ["verify", "--project", str(project)]).exit_code == 0
    expanded = runner.invoke(app, ["expand", "notarize", "--project", str(project)])
    assert expanded.exit_code == 0, expanded.output
    assert (project / ".agent/skills/notarize/SKILL.md").is_file()

    # Adding again from the same source does not duplicate it.
    again = runner.invoke(
        app, ["add", "@acme/notarize", "--project", str(project), "--source", str(source)]
    )
    assert again.exit_code == 0, again.output
    manifest = yaml.safe_load((project / "speccify.yaml").read_text(encoding="utf-8"))
    assert manifest["sources"] == [str(source)]


def test_add_names_a_source_that_is_not_on_disk(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    project = tmp_path / "project"
    assert runner.invoke(app, ["init", "--project", str(project)]).exit_code == 0
    result = runner.invoke(
        app,
        [
            "add",
            "@acme/notarize",
            "--project",
            str(project),
            "--source",
            "https://github.com/acme/skills.git",
        ],
    )
    assert result.exit_code == 1
    assert "not cloned yet" in result.output
    # Nothing was written for a source that could not be read.
    manifest = yaml.safe_load((project / "speccify.yaml").read_text(encoding="utf-8"))
    assert "sources" not in manifest
