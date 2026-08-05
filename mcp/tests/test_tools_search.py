"""Tests für das MCP-Tool `search` (Phase P5 Stufe 4)."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_mcp.tools import run_search
from speccify_mcp.tools.search import INDEX_ENV


@pytest.fixture
def project(tmp_path: Path) -> Path:
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
    return tmp_path


def test_search_uses_the_project_index_by_default(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(INDEX_ENV, raising=False)
    result = run_search(project, query="sterne")
    assert result.ok, result.message
    assert result.hits[0]["source"] == "git+https://github.com/acme/rating-stars"
    assert result.sources == [str(project / "index")]


def test_explicit_sources_win(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(INDEX_ENV, "/aus/der/env")
    result = run_search(project, query="", index_sources=[str(project / "index")])
    assert result.ok
    assert len(result.hits) == 1


def test_missing_index_is_a_structured_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(INDEX_ENV, raising=False)
    result = run_search(tmp_path, query="x")
    assert not result.ok
    assert result.code == "no_index_configured"


def test_broken_index_is_a_structured_answer(tmp_path: Path) -> None:
    entries = tmp_path / "entries"
    entries.mkdir()
    (entries / "kaputt.yaml").write_text("source: nur-müll\n", encoding="utf-8")
    result = run_search(tmp_path, query="x", index_sources=[str(tmp_path)])
    assert not result.ok
    assert result.code == "index_invalid"
    assert "kaputt.yaml" in result.message
