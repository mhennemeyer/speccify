"""Tests for `GitLibrary` — against real `file://` repositories.

No network: the fixtures are local git repos addressed via `file://`. That is
the same code path as `https://` (git only differs in transport) and keeps CI
hermetic.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from speccify_core import GitLibrary, GitLibraryError, Version, is_git_ref, parse_git_ref
from speccify_core.git_registry import GitRef

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")


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


def _playbook_yaml(playbook_id: str, version: str, title: str = "Fetched") -> str:
    return (
        "schema_version: 1\n"
        f"id: '{playbook_id}'\n"
        f"version: {version}\n"
        f"title: {title}\n"
        "summary: Loaded from a git repository.\n"
        "steps:\n"
        "  - id: only\n"
        "    title: The only step\n"
        "    detail: Do the thing.\n"
    )


@pytest.fixture
def single_playbook_repo(tmp_path: Path) -> str:
    """Repository with the bundle at the root and tags v0.1.0 / v0.2.0."""
    repo = tmp_path / "rating-stars"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch", "main")
    for version in ("0.1.0", "0.2.0"):
        (repo / "playbook.yaml").write_text(
            _playbook_yaml("@acme/rating-stars", version), encoding="utf-8"
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "--quiet", "-m", f"release {version}")
        _git(repo, "tag", f"v{version}")
    return f"git+file://{repo}"


@pytest.fixture
def multi_playbook_repo(tmp_path: Path) -> str:
    """Monorepo with two playbooks and path-prefixed tags."""
    repo = tmp_path / "kit"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch", "main")
    for name, version in (("button", "0.1.0"), ("text-input", "1.4.2"), ("button", "0.3.0")):
        target = repo / "playbooks" / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "playbook.yaml").write_text(
            _playbook_yaml(f"@acme/{name}", version, title=name), encoding="utf-8"
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "--quiet", "-m", f"{name} {version}")
        _git(repo, "tag", f"playbooks/{name}/v{version}")
    return f"git+file://{repo}"


# --- Ref parsing ---------------------------------------------------------------


def test_parse_git_ref_splits_url_and_path() -> None:
    ref = parse_git_ref("git+https://github.com/acme/kit#playbooks/button")
    assert ref == GitRef(url="https://github.com/acme/kit", path="playbooks/button")
    assert ref.playbook_path == "playbooks/button/playbook.yaml"
    assert ref.tag_for(Version.parse("1.2.0")) == "playbooks/button/v1.2.0"


def test_parse_git_ref_without_path() -> None:
    ref = parse_git_ref("git+https://github.com/acme/rating-stars")
    assert ref.path == ""
    assert ref.playbook_path == "playbook.yaml"
    assert ref.tag_for(Version.parse("1.2.0")) == "v1.2.0"
    assert ref.playbook_id == "git+https://github.com/acme/rating-stars"


@pytest.mark.parametrize(
    "playbook_id",
    [
        "@org/button",
        "git+ftp://host/repo",
        "git+/local/without/scheme",
        "git+https://host/repo#../escape",
    ],
)
def test_parse_git_ref_rejects_broken_ids(playbook_id: str) -> None:
    with pytest.raises(GitLibraryError):
        parse_git_ref(playbook_id)


def test_is_git_ref() -> None:
    assert is_git_ref("git+https://host/repo")
    assert not is_git_ref("@org/button")


def test_version_for_ignores_foreign_tags() -> None:
    ref = parse_git_ref("git+https://host/kit#playbooks/button")
    assert ref.version_for("playbooks/button/v1.0.0") == Version.parse("1.0.0")
    assert ref.version_for("playbooks/text-input/v1.0.0") is None
    assert ref.version_for("v1.0.0") is None
    assert ref.version_for("playbooks/button/release-1") is None


# --- Resolution against real repositories ------------------------------------------------


def test_list_versions_reads_tags(single_playbook_repo: str, tmp_path: Path) -> None:
    registry = GitLibrary(cache_dir=tmp_path / "cache")
    assert registry.list_versions(single_playbook_repo) == [
        Version.parse("0.1.0"),
        Version.parse("0.2.0"),
    ]


def test_fetch_returns_bundle_and_commit(single_playbook_repo: str, tmp_path: Path) -> None:
    registry = GitLibrary(cache_dir=tmp_path / "cache")
    bundle = registry.fetch(single_playbook_repo, Version.parse("0.1.0"))
    assert bundle.source_id == single_playbook_repo
    assert bundle.parsed()["version"] == "0.1.0"
    assert bundle.source_commit and len(bundle.source_commit) == 40
    # The pin is stable and points at the same tag.
    assert (
        registry.resolve_commit(single_playbook_repo, Version.parse("0.1.0"))
        == bundle.source_commit
    )
    # Different versions resolve to different commits.
    other = registry.fetch(single_playbook_repo, Version.parse("0.2.0"))
    assert other.source_commit != bundle.source_commit


def test_multi_playbook_repo_versions_are_independent(
    multi_playbook_repo: str, tmp_path: Path
) -> None:
    registry = GitLibrary(cache_dir=tmp_path / "cache")
    button = f"{multi_playbook_repo}#playbooks/button"
    text_input = f"{multi_playbook_repo}#playbooks/text-input"
    assert registry.list_versions(button) == [Version.parse("0.1.0"), Version.parse("0.3.0")]
    assert registry.list_versions(text_input) == [Version.parse("1.4.2")]
    assert registry.fetch(text_input, Version.parse("1.4.2")).parsed()["title"] == "text-input"


def test_unknown_version_names_the_available_ones(
    single_playbook_repo: str, tmp_path: Path
) -> None:
    registry = GitLibrary(cache_dir=tmp_path / "cache")
    with pytest.raises(GitLibraryError, match="available: 0.1.0, 0.2.0"):
        registry.fetch(single_playbook_repo, Version.parse("9.9.9"))


def test_missing_playbook_file_is_reported(multi_playbook_repo: str, tmp_path: Path) -> None:
    registry = GitLibrary(cache_dir=tmp_path / "cache")
    # The tag exists, but no bundle lives under that path.
    ghost = f"{multi_playbook_repo}#playbooks/ghost"
    with pytest.raises(GitLibraryError):
        registry.fetch(ghost, Version.parse("0.1.0"))


# --- Cache and offline ------------------------------------------------------------


def test_cache_is_a_bare_repo_and_survives_the_source(
    single_playbook_repo: str, tmp_path: Path
) -> None:
    """After one fetch everything is readable offline — even without the source."""
    cache = tmp_path / "cache"
    GitLibrary(cache_dir=cache).fetch(single_playbook_repo, Version.parse("0.2.0"))
    assert list(cache.glob("rating-stars-*/repo.git/HEAD"))

    shutil.rmtree(single_playbook_repo.removeprefix("git+file://"))
    offline = GitLibrary(cache_dir=cache, offline=True)
    assert offline.list_versions(single_playbook_repo) == [
        Version.parse("0.1.0"),
        Version.parse("0.2.0"),
    ]
    assert (
        offline.fetch(single_playbook_repo, Version.parse("0.2.0")).parsed()["version"] == "0.2.0"
    )


def test_offline_without_cache_fails_with_a_hint(single_playbook_repo: str, tmp_path: Path) -> None:
    registry = GitLibrary(cache_dir=tmp_path / "leer", offline=True)
    with pytest.raises(GitLibraryError, match="offline=True"):
        registry.list_versions(single_playbook_repo)


def test_via_is_the_stable_git_marker(tmp_path: Path) -> None:
    assert GitLibrary(cache_dir=tmp_path).via == "git"
