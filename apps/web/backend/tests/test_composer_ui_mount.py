"""Tests für den /ui-Mount (Desktop-A1): Backend serviert die gebaute
Composer-SPA same-origin, damit das Composer-Fenster der Desktop-App ohne
CORS/zweite Origin auskommt. Fehlt der Build, bleibt /ui einfach weg."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]


def _settings(composer_dist: Path) -> Settings:
    return Settings(
        project_root=REPO_ROOT,
        registry_path=REPO_ROOT / "registry-fixtures",
        cache_dir=REPO_ROOT / "tests" / "fixtures" / "llm-cache",
        composer_dist=composer_dist,
    )


def test_ui_mount_serves_spa_when_dist_exists(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>composer-marker</title>")

    client = TestClient(create_app(_settings(dist)))
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "composer-marker" in response.text
    # API bleibt daneben unverändert erreichbar (same-origin-Prinzip).
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_ui_mount_absent_without_dist(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path / "gibt-es-nicht")))
    assert client.get("/ui/").status_code == 404
    assert client.get("/api/v1/health").json() == {"status": "ok"}
