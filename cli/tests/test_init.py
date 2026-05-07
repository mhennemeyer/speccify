"""Smoke-Tests für `speccify init`."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from speccify_cli.__main__ import app
from speccify_core.manifest import ProjectManifest
from typer.testing import CliRunner

runner = CliRunner()


def _invoke_init(cwd: Path, *args: str) -> object:
    """Führt `speccify init` mit `cwd` als aktuellem Verzeichnis aus."""
    prev = Path.cwd()
    os.chdir(cwd)
    try:
        return runner.invoke(app, ["init", *args])
    finally:
        os.chdir(prev)


def test_init_creates_minimal_manifest(tmp_path: Path) -> None:
    result = _invoke_init(tmp_path, "my-app")
    assert result.exit_code == 0, result.output

    manifest_path = tmp_path / "my-app" / "speccify.yaml"
    assert manifest_path.is_file()

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert data == {"schema_version": 1, "target": "react", "dependencies": {}}


def test_init_default_target_is_react(tmp_path: Path) -> None:
    result = _invoke_init(tmp_path, "app1")
    assert result.exit_code == 0, result.output
    data = yaml.safe_load((tmp_path / "app1" / "speccify.yaml").read_text(encoding="utf-8"))
    assert data["target"] == "react"


def test_init_custom_target(tmp_path: Path) -> None:
    result = _invoke_init(tmp_path, "app2", "--target", "swiftui")
    assert result.exit_code == 0, result.output
    data = yaml.safe_load((tmp_path / "app2" / "speccify.yaml").read_text(encoding="utf-8"))
    assert data["target"] == "swiftui"


def test_init_manifest_is_loadable_by_project_manifest(tmp_path: Path) -> None:
    result = _invoke_init(tmp_path, "loadable")
    assert result.exit_code == 0, result.output
    manifest = ProjectManifest.load(tmp_path / "loadable" / "speccify.yaml")
    assert manifest.schema_version == 1
    assert manifest.target == "react"
    assert manifest.dependencies == {}


def test_init_succeeds_in_existing_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    result = _invoke_init(tmp_path, "empty")
    assert result.exit_code == 0, result.output
    assert (tmp_path / "empty" / "speccify.yaml").is_file()


def test_init_fails_when_directory_not_empty(tmp_path: Path) -> None:
    proj = tmp_path / "occupied"
    proj.mkdir()
    (proj / "README.md").write_text("hi", encoding="utf-8")

    result = _invoke_init(tmp_path, "occupied")
    assert result.exit_code == 1
    assert "fehlgeschlagen" in result.output or "✗" in result.output
    # Es darf kein Manifest geschrieben worden sein.
    assert not (proj / "speccify.yaml").exists()


def test_init_rejects_invalid_name(tmp_path: Path) -> None:
    result = _invoke_init(tmp_path, "foo/bar")
    assert result.exit_code == 1
