"""Smoke-Tests für `speccify pull` (Phase 1b Step 5b: LLM-Codegen + Replay-Cache)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from speccify_cli.__main__ import app
from speccify_core import LlmGeneratorPin, Lockfile
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"
CACHE_DIR = REPO_ROOT / "tests" / "fixtures" / "llm-cache"

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


def test_pull_renders_tsx_and_updates_lockfile(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)

    assert runner.invoke(app, ["lock", "--project", str(project)]).exit_code == 0

    out = project / "out"
    result = runner.invoke(
        app,
        [
            "pull",
            "--project",
            str(project),
            "--out",
            str(out),
            "--cache-dir",
            str(CACHE_DIR),
        ],
    )
    assert result.exit_code == 0, result.output

    rendered = out / "org" / "Button.tsx"
    assert rendered.is_file()
    data = rendered.read_bytes()
    expected = f"sha256:{hashlib.sha256(data).hexdigest()}"

    lock = Lockfile.load(project / "speccify.lock")
    button_entry = next(e for e in lock.entries if e.id == "@org/button")
    assert len(button_entry.generated_files_sha256) == 1
    assert button_entry.generated_files_sha256[0].path == "org/Button.tsx"
    assert button_entry.generated_files_sha256[0].sha256 == expected

    assert isinstance(button_entry.generator, LlmGeneratorPin)
    assert button_entry.generator.model == "bedrock/eu.anthropic.claude-opus-4-7"
    assert button_entry.generator.prompt_version == "0.1.0"
    assert button_entry.generator.seed == 1
    assert button_entry.generator.cache_key.startswith("sha256:")
    assert len(button_entry.generator.cache_key) == len("sha256:") + 64


def test_pull_is_deterministic(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)
    runner.invoke(app, ["lock", "--project", str(project)])

    out = project / "out"
    runner.invoke(
        app,
        ["pull", "--project", str(project), "--out", str(out), "--cache-dir", str(CACHE_DIR)],
    )
    first_lock = (project / "speccify.lock").read_bytes()
    first_file = (out / "org" / "Button.tsx").read_bytes()

    runner.invoke(
        app,
        ["pull", "--project", str(project), "--out", str(out), "--cache-dir", str(CACHE_DIR)],
    )
    second_lock = (project / "speccify.lock").read_bytes()
    second_file = (out / "org" / "Button.tsx").read_bytes()

    assert first_lock == second_lock
    assert first_file == second_file


def test_pull_fails_without_lockfile(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)

    result = runner.invoke(
        app,
        [
            "pull",
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


def test_pull_target_mismatch_fails(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)
    runner.invoke(app, ["lock", "--project", str(project)])

    result = runner.invoke(
        app,
        [
            "pull",
            "--project",
            str(project),
            "--out",
            str(project / "out"),
            "--target",
            "swiftui",
            "--cache-dir",
            str(CACHE_DIR),
        ],
    )
    assert result.exit_code == 1
    assert "weicht" in result.output or "Target" in result.output


def test_pull_offline_cache_miss_fails(tmp_path: Path) -> None:
    """Cache-Miss im `--offline`-Modus muss klar fehlschlagen (Exit 1)."""
    project = tmp_path / "proj"
    project.mkdir()
    _write_manifest(project, {"@org/button": "^0.1"}, FIXTURES)
    runner.invoke(app, ["lock", "--project", str(project)])

    empty_cache = tmp_path / "empty-cache"
    empty_cache.mkdir()
    result = runner.invoke(
        app,
        [
            "pull",
            "--project",
            str(project),
            "--out",
            str(project / "out"),
            "--cache-dir",
            str(empty_cache),
        ],
    )
    assert result.exit_code == 1
    assert "Cache-Miss" in result.output or "offline" in result.output.lower()
