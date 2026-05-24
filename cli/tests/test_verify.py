"""Smoke-Tests für `speccify verify` (Phase 1b Step 5b: LLM-Codegen + Replay-Cache)."""

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


def test_verify_happy_path(tmp_path: Path) -> None:
    project, out = _setup_project(tmp_path)
    result = runner.invoke(
        app,
        ["verify", "--project", str(project), "--out", str(out), "--cache-dir", str(CACHE_DIR)],
    )
    assert result.exit_code == 0, result.output
    assert "konsistent" in result.output


def test_verify_detects_disk_drift(tmp_path: Path) -> None:
    project, out = _setup_project(tmp_path)
    rendered = out / "org" / "Button.tsx"
    rendered.write_bytes(rendered.read_bytes() + b"\n// manually modified\n")

    result = runner.invoke(
        app,
        ["verify", "--project", str(project), "--out", str(out), "--cache-dir", str(CACHE_DIR)],
    )
    assert result.exit_code == 1
    assert "Disk-Drift" in result.output


def test_verify_fails_without_lockfile(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)
    result = runner.invoke(
        app,
        [
            "verify",
            "--project",
            str(project),
            "--out",
            str(project / "out"),
            "--cache-dir",
            str(CACHE_DIR),
        ],
    )
    assert result.exit_code == 1
    assert "speccify lock" in result.output


def test_verify_fails_when_pull_missing(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)
    runner.invoke(app, ["lock", "--project", str(project)])

    result = runner.invoke(
        app,
        [
            "verify",
            "--project",
            str(project),
            "--out",
            str(project / "out"),
            "--cache-dir",
            str(CACHE_DIR),
        ],
    )
    assert result.exit_code == 1
    assert "speccify pull" in result.output


def test_verify_detects_model_drift(tmp_path: Path) -> None:
    """Wenn das Lockfile einen abweichenden Modell-Pin enthält, muss verify Drift melden."""
    project, out = _setup_project(tmp_path)
    lock_path = project / "speccify.lock"
    raw = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    for spec in raw["specs"]:
        if spec["generator"].get("kind") == "llm":
            spec["generator"]["model"] = "bedrock/some-other-model"
    lock_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    result = runner.invoke(
        app,
        ["verify", "--project", str(project), "--out", str(out), "--cache-dir", str(CACHE_DIR)],
    )
    assert result.exit_code == 1
    assert "Modell-Drift" in result.output or "Cache-Key-Drift" in result.output


def test_verify_warns_on_yanked_lockfile_entry(tmp_path: Path) -> None:
    """Phase 2 Stage 5: yanked Versionen erzeugen Warnung, kein Fehlschlag."""
    project, out = _setup_project(tmp_path)
    lock_path = project / "speccify.lock"
    raw = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    for spec in raw["specs"]:
        if spec["id"] == "@org/button":
            spec["yank_status"] = "yanked"
            spec["yank_reason"] = "security issue"
    lock_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    result = runner.invoke(
        app,
        ["verify", "--project", str(project), "--out", str(out), "--cache-dir", str(CACHE_DIR)],
    )
    assert result.exit_code == 0, result.output
    assert "geyanked" in result.output
    assert "security issue" in result.output
    assert "konsistent" in result.output


def test_verify_offline_cache_miss_fails(tmp_path: Path) -> None:
    """`verify --cache-dir <leer>` muss bei Cache-Miss klar fehlschlagen."""
    project, out = _setup_project(tmp_path)
    empty_cache = tmp_path / "empty-cache"
    empty_cache.mkdir()
    result = runner.invoke(
        app,
        ["verify", "--project", str(project), "--out", str(out), "--cache-dir", str(empty_cache)],
    )
    assert result.exit_code == 1
    assert "Cache-Miss" in result.output or "offline" in result.output.lower()
