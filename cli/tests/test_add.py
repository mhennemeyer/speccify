"""Smoke-Tests für `speccify add`."""

from __future__ import annotations

from pathlib import Path

from speccify_cli.__main__ import app
from speccify_core import Lockfile, ProjectManifest
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"

runner = CliRunner()


def _empty_manifest(project_dir: Path) -> Path:
    manifest = project_dir / "speccify.yaml"
    manifest.write_text(
        f"schema_version: 1\ntarget: react\nregistry:\n  path: {FIXTURES}\ndependencies: {{}}\n",
        encoding="utf-8",
    )
    return manifest


def test_add_default_range_uses_caret_major_minor(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _empty_manifest(project)

    result = runner.invoke(app, ["add", "@org/button", "--project", str(project)])
    assert result.exit_code == 0, result.output

    manifest = ProjectManifest.load(project / "speccify.yaml")
    # Latest button-Version im Registry ist 0.1.1 → Default-Range '^0.1'
    assert manifest.dependencies == {"@org/button": "^0.1"}

    # Lockfile wurde implizit geschrieben.
    lock = Lockfile.load(project / "speccify.lock")
    ids = [e.id for e in lock.entries]
    assert "@org/button" in ids


def test_add_with_explicit_caret_range(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _empty_manifest(project)

    result = runner.invoke(app, ["add", "@org/button@^0.1.1", "--project", str(project)])
    assert result.exit_code == 0, result.output
    manifest = ProjectManifest.load(project / "speccify.yaml")
    assert manifest.dependencies == {"@org/button": "^0.1.1"}


def test_add_with_exact_version(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _empty_manifest(project)

    result = runner.invoke(app, ["add", "@org/button@0.1.0", "--project", str(project)])
    assert result.exit_code == 0, result.output
    manifest = ProjectManifest.load(project / "speccify.yaml")
    assert manifest.dependencies == {"@org/button": "0.1.0"}
    lock = Lockfile.load(project / "speccify.lock")
    button = next(e for e in lock.entries if e.id == "@org/button")
    assert button.version == "0.1.0"


def test_add_unknown_spec_fails(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _empty_manifest(project)

    result = runner.invoke(app, ["add", "@org/does-not-exist", "--project", str(project)])
    assert result.exit_code == 1, result.output


def test_add_invalid_spec_ref(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _empty_manifest(project)

    result = runner.invoke(app, ["add", "not-an-id", "--project", str(project)])
    assert result.exit_code != 0
