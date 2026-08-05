"""Tests für `speccify search` (Phase P5 Stufe 3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from speccify_cli.__main__ import app
from speccify_cli.commands.search import INDEX_ENV, resolve_index_sources
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    entries = tmp_path / "index" / "entries"
    entries.mkdir(parents=True)
    (entries / "rating-stars.yaml").write_text(
        "schema_version: 1\n"
        "source: git+https://github.com/acme/rating-stars\n"
        "title: Rating Stars\n"
        "summary: Sternebewertung mit halben Sternen.\n"
        "kind: ui-component\n"
        "keywords: [rating, stars]\n",
        encoding="utf-8",
    )
    return tmp_path / "index"


def test_search_finds_and_prints_the_entry(index_dir: Path) -> None:
    result = runner.invoke(app, ["search", "sterne", "--index", str(index_dir)])
    assert result.exit_code == 0, result.output
    assert "Rating Stars" in result.output
    assert "git+https://github.com/acme/rating-stars" in result.output
    assert "1 Treffer" in result.output


def test_search_json_is_machine_readable(index_dir: Path) -> None:
    result = runner.invoke(app, ["search", "rating", "--index", str(index_dir), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["query"] == "rating"
    assert payload["hits"][0]["source"] == "git+https://github.com/acme/rating-stars"
    assert payload["hits"][0]["keywords"] == ["rating", "stars"]


def test_search_without_hits_says_so(index_dir: Path) -> None:
    result = runner.invoke(app, ["search", "gibtsnicht", "--index", str(index_dir)])
    assert result.exit_code == 0
    assert "Keine Treffer" in result.output


def test_search_without_any_index_source_explains_the_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(INDEX_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["search", "irgendwas"])
    assert result.exit_code == 1
    assert "Keine Index-Quelle konfiguriert" in result.output


def test_broken_index_fails_with_the_file_name(tmp_path: Path) -> None:
    entries = tmp_path / "entries"
    entries.mkdir()
    (entries / "kaputt.yaml").write_text("source: nur-müll\n", encoding="utf-8")
    result = runner.invoke(app, ["search", "x", "--index", str(tmp_path)])
    assert result.exit_code == 1
    assert "kaputt.yaml" in result.output


def test_source_resolution_order(
    tmp_path: Path, index_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--index` schlägt Env, Env schlägt `./index`."""
    monkeypatch.chdir(index_dir.parent)
    monkeypatch.setenv(INDEX_ENV, "/aus/der/env")
    assert resolve_index_sources(["/explizit"]) == [Path("/explizit")]
    assert resolve_index_sources(None) == [Path("/aus/der/env")]
    monkeypatch.delenv(INDEX_ENV)
    assert resolve_index_sources(None) == [index_dir.parent / "index"]


def test_env_accepts_several_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(INDEX_ENV, "/eins,git+https://host/zwei")
    assert resolve_index_sources(None) == [Path("/eins"), "git+https://host/zwei"]
