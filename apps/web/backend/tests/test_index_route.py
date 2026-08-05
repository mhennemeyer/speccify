"""Tests für `GET /api/v1/index` (Discovery über HTTP, Phase P5 Stufe 4)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]


def _client(index_sources: tuple[str, ...] = ()) -> TestClient:
    settings = Settings(
        project_root=REPO_ROOT,
        registry_path=REPO_ROOT / "registry-fixtures",
        cache_dir=REPO_ROOT / "tests" / "fixtures" / "llm-cache",
        index_sources=index_sources,
    )
    return TestClient(create_app(settings))


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    entries = tmp_path / "entries"
    entries.mkdir()
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


def test_index_search_returns_hits(index_dir: Path) -> None:
    response = _client((str(index_dir),)).get("/api/v1/index", params={"q": "sterne"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["query"] == "sterne"
    assert body["hits"][0]["source"] == "git+https://github.com/acme/rating-stars"
    assert body["hits"][0]["keywords"] == ["rating", "stars"]


def test_empty_query_lists_everything(index_dir: Path) -> None:
    body = _client((str(index_dir),)).get("/api/v1/index").json()
    assert len(body["hits"]) == 1


def test_source_can_be_overridden_per_request(index_dir: Path) -> None:
    response = _client().get("/api/v1/index", params={"source": str(index_dir)})
    assert response.status_code == 200
    assert response.json()["sources"] == [str(index_dir)]


def test_without_configured_index_is_404() -> None:
    response = _client().get("/api/v1/index")
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "no_index_configured"


def test_broken_index_is_422(tmp_path: Path) -> None:
    entries = tmp_path / "entries"
    entries.mkdir()
    (entries / "kaputt.yaml").write_text("source: nur-müll\n", encoding="utf-8")
    response = _client((str(tmp_path),)).get("/api/v1/index")
    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "index_invalid"
