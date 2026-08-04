"""End-to-End: ein Projekt, dessen Dependency aus einem Git-Repo kommt (Phase P5 Stufe 2).

`lock` → `pull` → `verify` gegen eine echte Git-Quelle (lokales `file://`-Repo,
kein Netz). Geprüft wird der ganze Determinismus-Stack auf dem neuen Pfad:
Tag-Auflösung, Commit-Pin im Lockfile v4, Offline-Reproduzierbarkeit.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from speccify_cli.__main__ import app
from speccify_core import Lockfile
from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "tests" / "fixtures" / "llm-cache"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git nicht im PATH")

runner = CliRunner()


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            "PATH": os.environ.get("PATH", ""),
            "GIT_AUTHOR_NAME": "Speccify Test",
            "GIT_AUTHOR_EMAIL": "test@speccify.io",
            "GIT_COMMITTER_NAME": "Speccify Test",
            "GIT_COMMITTER_EMAIL": "test@speccify.io",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )


@pytest.fixture
def spec_repo(tmp_path: Path) -> str:
    """Spec-Repo mit `@org/button@0.1.0` unter zwei Tags."""
    source = REPO_ROOT / "registry-fixtures" / "org" / "button" / "0.1.0" / "spec.speccify.yaml"
    repo = tmp_path / "button-repo"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch", "main")
    (repo / "spec.speccify.yaml").write_bytes(source.read_bytes())
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "button 0.1.0")
    _git(repo, "tag", "v0.1.0")
    return f"git+file://{repo}"


@pytest.fixture
def project(tmp_path: Path, spec_repo: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Projekt, dessen einzige Dependency die Git-Quelle ist."""
    monkeypatch.setenv("SPECCIFY_GIT_CACHE", str(tmp_path / "git-cache"))
    project_dir = tmp_path / "projekt"
    project_dir.mkdir()
    (project_dir / "speccify.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "targets": ["react"],
                "registry": {"path": str(REPO_ROOT / "registry-fixtures")},
                "dependencies": {spec_repo: "^0.1"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return project_dir


def test_lock_resolves_the_git_tag_and_pins_the_commit(
    project: Path, spec_repo: str, tmp_path: Path
) -> None:
    result = runner.invoke(app, ["lock", "--project", str(project)])
    assert result.exit_code == 0, result.output

    lockfile = Lockfile.load(project / "speccify.lock")
    assert lockfile.schema_version == 4
    entry = next(e for e in lockfile.entries if e.id == spec_repo)
    assert entry.version == "0.1.0"
    assert entry.resolved_via == "git"
    assert entry.source_commit and len(entry.source_commit) == 40


def test_pull_and_verify_run_offline_against_the_cache(project: Path, spec_repo: str) -> None:
    assert runner.invoke(app, ["lock", "--project", str(project)]).exit_code == 0

    out = project / "out"
    pull = runner.invoke(
        app,
        [
            "pull",
            "--project",
            str(project),
            "--offline",
            "--cache-dir",
            str(CACHE_DIR),
            "--out",
            str(out),
        ],
    )
    assert pull.exit_code == 0, pull.output
    assert (out / "org" / "Button.tsx").is_file()

    # Die Quelle ist weg — dank Bare-Clone-Cache bleibt `verify` reproduzierbar.
    shutil.rmtree(spec_repo.removeprefix("git+file://"))
    verify = runner.invoke(
        app,
        [
            "verify",
            "--project",
            str(project),
            "--offline",
            "--cache-dir",
            str(CACHE_DIR),
            "--out",
            str(out),
        ],
    )
    assert verify.exit_code == 0, verify.output


def test_missing_tag_is_reported(project: Path, spec_repo: str) -> None:
    """Range, die kein Tag erfüllt → klarer Resolver-Fehler statt Stacktrace."""
    manifest = project / "speccify.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace("^0.1", "^9.0"), encoding="utf-8"
    )
    result = runner.invoke(app, ["lock", "--project", str(project)])
    assert result.exit_code == 1
    assert spec_repo in result.output
