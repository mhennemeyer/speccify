"""CLI-Smoke-Tests für `speccify conformance` (Phase 3 Stage 4)."""

from __future__ import annotations

from pathlib import Path

import yaml
from speccify_cli.__main__ import app
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"
CACHE_DIR = REPO_ROOT / "tests" / "fixtures" / "llm-cache"

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
    assert (
        runner.invoke(
            app,
            ["pull", "--project", str(project), "--out", str(out), "--cache-dir", str(CACHE_DIR)],
        ).exit_code
        == 0
    )
    return project, out


def test_conformance_happy_path(tmp_path: Path) -> None:
    project, _ = _setup_project(tmp_path)
    result = runner.invoke(
        app,
        ["conformance", "--project", str(project), "--cache-dir", str(CACHE_DIR)],
    )
    assert result.exit_code == 0, result.output
    assert "Pfade ok" in result.output
    assert "static-validate" in result.output


def test_conformance_target_filter_skips_unrelated_targets(tmp_path: Path) -> None:
    project, _ = _setup_project(tmp_path)
    result = runner.invoke(
        app,
        [
            "conformance",
            "--project",
            str(project),
            "--cache-dir",
            str(CACHE_DIR),
            "-t",
            "swiftui",
        ],
    )
    # React-only-Lockfile + Filter auf swiftui → 0 Results, alle ok.
    assert result.exit_code == 0, result.output
    assert "0 Pfade ok" in result.output


def test_conformance_detects_hash_drift(tmp_path: Path) -> None:
    project, _ = _setup_project(tmp_path)
    lock_path = project / "speccify.lock"
    data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    # Setze einen Output-Hash auf einen offensichtlichen Müll-Wert.
    data["specs"][0]["generated_files_sha256"][0]["sha256"] = "sha256:" + "f" * 64
    lock_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = runner.invoke(
        app,
        ["conformance", "--project", str(project), "--cache-dir", str(CACHE_DIR)],
    )
    assert result.exit_code == 1, result.output
    assert "hash_drift" in result.output


def test_conformance_fails_without_lockfile(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)
    result = runner.invoke(
        app,
        ["conformance", "--project", str(project), "--cache-dir", str(CACHE_DIR)],
    )
    assert result.exit_code == 1
    assert "kein Lockfile" in result.output
