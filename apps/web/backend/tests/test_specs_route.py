"""Tests for `GET /api/v1/specs`.

Uses the repo-default registry (`registry-fixtures/`) — same source the MCP
and CLI adapters resolve against, so the playground lists exactly the specs
that also have replay-cache entries.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
LLM_CACHE = REPO_ROOT / "tests" / "fixtures" / "llm-cache"


def _client(tmp_path: Path | None = None, *, registry_path: Path | None = None) -> TestClient:
    settings = Settings(
        project_root=tmp_path if tmp_path is not None else REPO_ROOT,
        registry_path=registry_path if registry_path is not None else REGISTRY_FIXTURES,
        cache_dir=LLM_CACHE,
    )
    return TestClient(create_app(settings=settings))


def test_list_specs_returns_registry_entries() -> None:
    client = _client()
    response = client.get("/api/v1/specs")
    assert response.status_code == 200
    body = response.json()
    assert "specs" in body
    ids = [entry["id"] for entry in body["specs"]]
    assert "@org/button" in ids

    by_id = {entry["id"]: entry for entry in body["specs"]}
    button = by_id["@org/button"]
    # Two versions exist for @org/button (0.1.0, 0.1.1); we surface the latest.
    assert button["version"] == "0.1.1"
    assert button["yaml"].startswith("schema_version: 1")
    # Title is extracted from YAML when present.
    assert isinstance(button["title"], str) and button["title"]


def test_list_specs_empty_when_registry_missing(tmp_path: Path) -> None:
    client = _client(tmp_path=tmp_path, registry_path=tmp_path / "does-not-exist")
    response = client.get("/api/v1/specs")
    assert response.status_code == 200
    assert response.json() == {"specs": []}


def test_default_settings_resolve_to_existing_repo_dirs(monkeypatch) -> None:
    """Regression: the default registry/cache paths must point at the real repo
    checkout, not at `<repo>/apps/...`. A wrong `_REPO_ROOT` made the playground
    list zero specs out-of-the-box.
    """
    monkeypatch.delenv("SPECCIFY_REGISTRY_PATH", raising=False)
    monkeypatch.delenv("SPECCIFY_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("SPECCIFY_CACHE_DIR", raising=False)

    settings = Settings.from_env()
    assert settings.registry_path == REGISTRY_FIXTURES
    assert settings.registry_path.is_dir()
    assert settings.project_root == REPO_ROOT

    # And the default-config app actually lists specs from that directory.
    response = TestClient(create_app(settings=settings)).get("/api/v1/specs")
    assert response.status_code == 200
    assert response.json()["specs"], "default registry path must yield specs"
