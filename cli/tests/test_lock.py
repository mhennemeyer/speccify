"""Smoke-Tests für `speccify lock`."""

from __future__ import annotations

import shutil
from pathlib import Path

from speccify_cli.__main__ import app
from speccify_core import Lockfile
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"

runner = CliRunner()


def _write_manifest(project_dir: Path, deps: dict[str, str], registry: Path) -> Path:
    manifest = project_dir / "speccify.yaml"
    deps_block = "\n".join(f'  "{k}": "{v}"' for k, v in deps.items()) or "  {}"
    manifest.write_text(
        "schema_version: 1\n"
        "target: react\n"
        f"registry:\n  path: {registry}\n"
        "dependencies:\n" + deps_block + "\n",
        encoding="utf-8",
    )
    return manifest


def test_lock_writes_lockfile_for_example_project(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)

    result = runner.invoke(app, ["lock", "--project", str(project)])
    assert result.exit_code == 0, result.output

    lock_path = project / "speccify.lock"
    assert lock_path.is_file()
    lock = Lockfile.load(lock_path)
    assert lock.target == "react"
    ids = [e.id for e in lock.entries]
    assert "@org/button" in ids
    assert ids == sorted(ids)
    for e in lock.entries:
        assert e.generated_files_sha256 == ()


def test_lock_is_deterministic(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/contact-form": "^0.1"}, FIXTURES)

    r1 = runner.invoke(app, ["lock", "--project", str(project)])
    assert r1.exit_code == 0, r1.output
    first = (project / "speccify.lock").read_bytes()

    r2 = runner.invoke(app, ["lock", "--project", str(project)])
    assert r2.exit_code == 0, r2.output
    second = (project / "speccify.lock").read_bytes()
    assert first == second


def test_lock_fails_on_unknown_dependency(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/does-not-exist": "^0.1"}, FIXTURES)

    result = runner.invoke(app, ["lock", "--project", str(project)])
    assert result.exit_code == 1
    assert "fehlgeschlagen" in result.output or "✗" in result.output


def test_lock_fails_without_manifest(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    result = runner.invoke(app, ["lock", "--project", str(project)])
    assert result.exit_code == 1


def test_lock_uses_registry_override(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    bogus = tmp_path / "bogus-registry"
    shutil.copytree(FIXTURES, bogus)
    _write_manifest(project, {"@org/button": "^0.1"}, Path("/nonexistent"))

    result = runner.invoke(
        app,
        ["lock", "--project", str(project), "--registry", str(bogus)],
    )
    assert result.exit_code == 0, result.output
    assert (project / "speccify.lock").is_file()
