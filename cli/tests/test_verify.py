"""Smoke-Tests für `speccify verify`: Happy-Path und Drift-Detection."""

from __future__ import annotations

from pathlib import Path

from speccify_cli.__main__ import app
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"

runner = CliRunner()


def _write_manifest(project_dir: Path, deps: dict[str, str], registry: Path) -> None:
    manifest = project_dir / "speccify.yaml"
    deps_block = "\n".join(f'  "{k}": "{v}"' for k, v in deps.items()) or "  {}"
    manifest.write_text(
        "schema_version: 1\n"
        "target: react\n"
        f"registry:\n  path: {registry}\n"
        "dependencies:\n" + deps_block + "\n",
        encoding="utf-8",
    )


def _setup_project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)
    out = project / "out"
    assert runner.invoke(app, ["lock", "--project", str(project)]).exit_code == 0
    assert runner.invoke(app, ["pull", "--project", str(project), "--out", str(out)]).exit_code == 0
    return project, out


def test_verify_happy_path(tmp_path: Path) -> None:
    project, out = _setup_project(tmp_path)
    result = runner.invoke(app, ["verify", "--project", str(project), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "konsistent" in result.output


def test_verify_detects_disk_drift(tmp_path: Path) -> None:
    project, out = _setup_project(tmp_path)
    rendered = out / "org" / "button.md"
    rendered.write_bytes(rendered.read_bytes() + b"\n<!-- manually modified -->\n")

    result = runner.invoke(app, ["verify", "--project", str(project), "--out", str(out)])
    assert result.exit_code == 1
    assert "Disk-Drift" in result.output


def test_verify_fails_without_lockfile(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)
    result = runner.invoke(
        app, ["verify", "--project", str(project), "--out", str(project / "out")]
    )
    assert result.exit_code == 1
    assert "speccify lock" in result.output


def test_verify_fails_when_pull_missing(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)
    runner.invoke(app, ["lock", "--project", str(project)])

    result = runner.invoke(
        app, ["verify", "--project", str(project), "--out", str(project / "out")]
    )
    assert result.exit_code == 1
    assert "speccify pull" in result.output
