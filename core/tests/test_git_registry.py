"""Tests für `GitRegistry` (Phase P5 Stufe 1) — gegen echte `file://`-Repos.

Kein Netz: die Fixtures sind lokale Git-Repos, angesprochen über `file://`.
Das ist derselbe Codepfad wie bei `https://` (git unterscheidet nur im
Transport) und hält CI offline-fähig.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from speccify_core import GitRegistry, GitRegistryError, Version, is_git_ref, parse_git_ref
from speccify_core.git_registry import GitRef

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git nicht im PATH")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            "PATH": __import__("os").environ.get("PATH", ""),
            "GIT_AUTHOR_NAME": "Speccify Test",
            "GIT_AUTHOR_EMAIL": "test@speccify.io",
            "GIT_COMMITTER_NAME": "Speccify Test",
            "GIT_COMMITTER_EMAIL": "test@speccify.io",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )


def _spec_yaml(spec_id: str, version: str, title: str = "Button") -> str:
    return (
        "schema_version: 1\n"
        f"id: '{spec_id}'\n"
        f"version: {version}\n"
        "kind: ui-component\n"
        f"title: {title}\n"
        "summary: Aus einem Git-Repo geladen.\n"
        "api:\n"
        "  props:\n"
        "    - name: label\n"
        "      type: string\n"
        "      required: true\n"
    )


@pytest.fixture
def single_spec_repo(tmp_path: Path) -> str:
    """Repo mit der Spec im Root und den Tags v0.1.0 / v0.2.0."""
    repo = tmp_path / "rating-stars"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch", "main")
    for version in ("0.1.0", "0.2.0"):
        (repo / "spec.speccify.yaml").write_text(
            _spec_yaml("@acme/rating-stars", version), encoding="utf-8"
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "--quiet", "-m", f"release {version}")
        _git(repo, "tag", f"v{version}")
    return f"git+file://{repo}"


@pytest.fixture
def multi_spec_repo(tmp_path: Path) -> str:
    """Monorepo mit zwei Specs und pfad-präfixierten Tags (D17)."""
    repo = tmp_path / "kit"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch", "main")
    for name, version in (("button", "0.1.0"), ("text-input", "1.4.2"), ("button", "0.3.0")):
        target = repo / "specs" / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "spec.speccify.yaml").write_text(
            _spec_yaml(f"@acme/{name}", version, title=name), encoding="utf-8"
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "--quiet", "-m", f"{name} {version}")
        _git(repo, "tag", f"specs/{name}/v{version}")
    return f"git+file://{repo}"


# --- Ref-Parsing ---------------------------------------------------------------


def test_parse_git_ref_splits_url_and_path() -> None:
    ref = parse_git_ref("git+https://github.com/acme/kit#specs/button")
    assert ref == GitRef(url="https://github.com/acme/kit", path="specs/button")
    assert ref.spec_path == "specs/button/spec.speccify.yaml"
    assert ref.tag_for(Version.parse("1.2.0")) == "specs/button/v1.2.0"


def test_parse_git_ref_without_path() -> None:
    ref = parse_git_ref("git+https://github.com/acme/rating-stars")
    assert ref.path == ""
    assert ref.spec_path == "spec.speccify.yaml"
    assert ref.tag_for(Version.parse("1.2.0")) == "v1.2.0"
    assert ref.spec_id == "git+https://github.com/acme/rating-stars"


@pytest.mark.parametrize(
    "spec_id",
    [
        "@org/button",
        "git+ftp://host/repo",
        "git+/lokal/ohne/schema",
        "git+https://host/repo#../ausbruch",
    ],
)
def test_parse_git_ref_rejects_broken_ids(spec_id: str) -> None:
    with pytest.raises(GitRegistryError):
        parse_git_ref(spec_id)


def test_is_git_ref() -> None:
    assert is_git_ref("git+https://host/repo")
    assert not is_git_ref("@org/button")


def test_version_for_ignores_foreign_tags() -> None:
    ref = parse_git_ref("git+https://host/kit#specs/button")
    assert ref.version_for("specs/button/v1.0.0") == Version.parse("1.0.0")
    assert ref.version_for("specs/text-input/v1.0.0") is None
    assert ref.version_for("v1.0.0") is None
    assert ref.version_for("specs/button/release-1") is None


# --- Auflösung gegen echte Repos ------------------------------------------------


def test_list_versions_reads_tags(single_spec_repo: str, tmp_path: Path) -> None:
    registry = GitRegistry(cache_dir=tmp_path / "cache")
    assert registry.list_versions(single_spec_repo) == [
        Version.parse("0.1.0"),
        Version.parse("0.2.0"),
    ]


def test_fetch_returns_spec_bytes_and_commit(single_spec_repo: str, tmp_path: Path) -> None:
    registry = GitRegistry(cache_dir=tmp_path / "cache")
    spec = registry.fetch(single_spec_repo, Version.parse("0.1.0"))
    assert spec.spec_id == single_spec_repo
    assert spec.parsed()["version"] == "0.1.0"
    assert spec.source_commit and len(spec.source_commit) == 40
    # Der Commit-Pin ist stabil und zeigt auf denselben Tag.
    assert registry.resolve_commit(single_spec_repo, Version.parse("0.1.0")) == spec.source_commit
    # Verschiedene Versionen → verschiedene Commits.
    other = registry.fetch(single_spec_repo, Version.parse("0.2.0"))
    assert other.source_commit != spec.source_commit


def test_multi_spec_repo_versions_are_independent(multi_spec_repo: str, tmp_path: Path) -> None:
    registry = GitRegistry(cache_dir=tmp_path / "cache")
    button = f"{multi_spec_repo}#specs/button"
    text_input = f"{multi_spec_repo}#specs/text-input"
    assert registry.list_versions(button) == [Version.parse("0.1.0"), Version.parse("0.3.0")]
    assert registry.list_versions(text_input) == [Version.parse("1.4.2")]
    assert registry.fetch(text_input, Version.parse("1.4.2")).parsed()["title"] == "text-input"


def test_unknown_version_names_the_available_ones(single_spec_repo: str, tmp_path: Path) -> None:
    registry = GitRegistry(cache_dir=tmp_path / "cache")
    with pytest.raises(GitRegistryError, match="verfügbar: 0.1.0, 0.2.0"):
        registry.fetch(single_spec_repo, Version.parse("9.9.9"))


def test_missing_spec_file_is_reported(multi_spec_repo: str, tmp_path: Path) -> None:
    registry = GitRegistry(cache_dir=tmp_path / "cache")
    # Tag existiert (specs/button/v0.1.0), aber unter diesem Pfad liegt keine Spec.
    ghost = f"{multi_spec_repo}#specs/ghost"
    with pytest.raises(GitRegistryError):
        registry.fetch(ghost, Version.parse("0.1.0"))


# --- Cache & offline ------------------------------------------------------------


def test_cache_is_a_bare_repo_and_survives_the_source(
    single_spec_repo: str, tmp_path: Path
) -> None:
    """Nach einem Fetch ist alles offline lesbar — auch ohne die Quelle."""
    cache = tmp_path / "cache"
    GitRegistry(cache_dir=cache).fetch(single_spec_repo, Version.parse("0.2.0"))
    assert list(cache.glob("rating-stars-*/repo.git/HEAD"))

    shutil.rmtree(single_spec_repo.removeprefix("git+file://"))
    offline = GitRegistry(cache_dir=cache, offline=True)
    assert offline.list_versions(single_spec_repo) == [
        Version.parse("0.1.0"),
        Version.parse("0.2.0"),
    ]
    assert offline.fetch(single_spec_repo, Version.parse("0.2.0")).parsed()["version"] == "0.2.0"


def test_offline_without_cache_fails_with_a_hint(single_spec_repo: str, tmp_path: Path) -> None:
    registry = GitRegistry(cache_dir=tmp_path / "leer", offline=True)
    with pytest.raises(GitRegistryError, match="offline=True"):
        registry.list_versions(single_spec_repo)


def test_via_is_the_stable_git_marker(tmp_path: Path) -> None:
    assert GitRegistry(cache_dir=tmp_path).via == "git"
