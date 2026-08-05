"""Tests für Discovery-Indizes (Phase P5 Stufe 3)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from speccify_core import (
    GitRepoCache,
    SpecIndexError,
    load_index,
    load_indexes,
    parse_index_entry,
    search_index,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _entry(source: str, title: str, summary: str, keywords: str = "[rating, stars]") -> str:
    return (
        "schema_version: 1\n"
        f"source: {source}\n"
        f"title: {title}\n"
        f"summary: {summary}\n"
        "kind: ui-component\n"
        f"keywords: {keywords}\n"
        "license: MIT\n"
    )


@pytest.fixture
def local_index(tmp_path: Path) -> Path:
    entries = tmp_path / "index" / "entries"
    entries.mkdir(parents=True)
    (entries / "rating-stars.yaml").write_text(
        _entry(
            "git+https://github.com/acme/rating-stars",
            "Rating Stars",
            "Sternebewertung mit halben Sternen.",
        ),
        encoding="utf-8",
    )
    (entries / "button.yaml").write_text(
        _entry(
            "git+https://github.com/acme/kit#specs/button",
            "Button",
            "Knopf mit Varianten und Ladezustand.",
            keywords="[button, form]",
        ),
        encoding="utf-8",
    )
    (entries / "notizen.txt").write_text("kein Eintrag", encoding="utf-8")
    return tmp_path / "index"


# --- Laden & Validieren ---------------------------------------------------------


def test_load_local_index_reads_all_entries(local_index: Path) -> None:
    entries = load_index(local_index)
    assert {entry.source for entry in entries} == {
        "git+https://github.com/acme/rating-stars",
        "git+https://github.com/acme/kit#specs/button",
    }
    stars = next(e for e in entries if e.title == "Rating Stars")
    assert stars.keywords == ("rating", "stars")
    assert stars.license == "MIT"
    assert stars.origin == str(local_index)


def test_entries_dir_is_optional_in_the_path(local_index: Path) -> None:
    """`--index <repo>` und `--index <repo>/entries` finden dieselben Einträge.

    Nur `origin` unterscheidet sich — das ist der angegebene Pfad selbst.
    """
    direct = load_index(local_index / "entries")
    via_root = load_index(local_index)
    assert [e.source for e in direct] == [e.source for e in via_root]


def test_broken_entry_names_file_and_problem(tmp_path: Path) -> None:
    entries = tmp_path / "entries"
    entries.mkdir()
    (entries / "kaputt.yaml").write_text(
        "schema_version: 1\nsource: https://kein-git-ref\ntitle: X\nsummary: Y\n",
        encoding="utf-8",
    )
    with pytest.raises(SpecIndexError, match="kaputt.yaml"):
        load_index(tmp_path)


def test_unknown_keys_are_rejected(tmp_path: Path) -> None:
    entries = tmp_path / "entries"
    entries.mkdir()
    (entries / "extra.yaml").write_text(
        "schema_version: 1\n"
        "source: git+https://github.com/acme/x\n"
        "title: X\n"
        "summary: Y\n"
        "downloads: 12000\n",
        encoding="utf-8",
    )
    with pytest.raises(SpecIndexError, match="downloads"):
        load_index(tmp_path)


def test_duplicate_source_in_one_index_is_an_error(local_index: Path) -> None:
    (local_index / "entries" / "kopie.yaml").write_text(
        _entry(
            "git+https://github.com/acme/rating-stars",
            "Rating Stars (Kopie)",
            "Doppelt eingetragen.",
        ),
        encoding="utf-8",
    )
    with pytest.raises(SpecIndexError, match="doppelt"):
        load_index(local_index)


def test_parse_entry_requires_a_git_source() -> None:
    with pytest.raises(SpecIndexError, match="source"):
        parse_index_entry(
            b"schema_version: 1\nsource: '@org/button'\ntitle: X\nsummary: Y\n",
            origin="test",
            name="x.yaml",
        )


# --- Mehrere Quellen ------------------------------------------------------------


def test_first_source_wins_across_indexes(local_index: Path, tmp_path: Path) -> None:
    second = tmp_path / "zweiter" / "entries"
    second.mkdir(parents=True)
    second.joinpath("rating-stars.yaml").write_text(
        _entry(
            "git+https://github.com/acme/rating-stars",
            "Rating Stars (Fork-Index)",
            "Anderer Index, gleiche Quelle.",
        ),
        encoding="utf-8",
    )
    merged = load_indexes([local_index, tmp_path / "zweiter"])
    stars = next(e for e in merged if "rating-stars" in e.source)
    assert stars.title == "Rating Stars"  # erste Quelle gewinnt
    assert len(merged) == 2


# --- Suche ----------------------------------------------------------------------


def test_search_ranks_id_before_title_before_keyword(local_index: Path) -> None:
    entries = load_index(local_index)
    assert [e.title for e in search_index(entries, "button")] == ["Button"]
    assert [e.title for e in search_index(entries, "sternen")] == ["Rating Stars"]
    assert search_index(entries, "gibtsnicht") == []


def test_empty_query_lists_everything(local_index: Path) -> None:
    assert len(search_index(load_index(local_index), "")) == 2


def test_search_is_case_insensitive(local_index: Path) -> None:
    assert [e.title for e in search_index(load_index(local_index), "RATING")] == ["Rating Stars"]


# --- Git-Index ------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git nicht im PATH")
def test_git_index_is_readable_and_cached(local_index: Path, tmp_path: Path) -> None:
    repo = tmp_path / "spec-index"
    shutil.copytree(local_index, repo)
    env = {
        "PATH": os.environ.get("PATH", ""),
        "GIT_AUTHOR_NAME": "Speccify Test",
        "GIT_AUTHOR_EMAIL": "test@speccify.io",
        "GIT_COMMITTER_NAME": "Speccify Test",
        "GIT_COMMITTER_EMAIL": "test@speccify.io",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }
    for args in (
        ["init", "--quiet", "--initial-branch", "main"],
        ["add", "."],
        ["commit", "--quiet", "-m", "index"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=env)

    source = f"git+file://{repo}"
    cache = GitRepoCache(cache_dir=tmp_path / "cache")
    entries = load_index(source, cache=cache)
    assert {e.title for e in entries} == {"Rating Stars", "Button"}
    assert all(e.origin == source for e in entries)

    # Nach dem ersten Lesen ist der Index offline verfügbar — auch ohne Quelle.
    shutil.rmtree(repo)
    offline = GitRepoCache(cache_dir=tmp_path / "cache", offline=True)
    assert len(load_index(source, cache=offline)) == 2


@pytest.mark.skipif(shutil.which("git") is None, reason="git nicht im PATH")
def test_git_index_without_cache_and_offline_fails_clearly(tmp_path: Path) -> None:
    cache = GitRepoCache(cache_dir=tmp_path / "leer", offline=True)
    with pytest.raises(SpecIndexError, match="offline=True"):
        load_index("git+https://example.invalid/spec-index", cache=cache)


# --- Der Index dieses Repos -----------------------------------------------------


def test_repo_index_is_valid() -> None:
    """CI-Gate für PRs an `index/`: jeder Eintrag valide, keine Quelle doppelt."""
    entries = load_index(REPO_ROOT / "index")
    assert isinstance(entries, list)
