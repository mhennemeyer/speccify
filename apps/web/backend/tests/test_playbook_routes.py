"""Tests for the playbook HTTP routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN = "@speccify/macos-notarize-tauri"


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        project_root=REPO_ROOT,
        library_path=REPO_ROOT / "playbooks",
    )
    return TestClient(create_app(settings))


def test_list_playbooks(client: TestClient) -> None:
    body = client.get("/api/v1/playbooks").json()
    ids = {entry["id"] for entry in body["playbooks"]}
    assert MAIN in ids


def test_get_playbook_resolves_sources(client: TestClient) -> None:
    response = client.get("/api/v1/playbook", params={"source": MAIN})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == "1.0.0"
    assert len(body["steps"]) == 5
    assert body["uses"] == ["@speccify/apple-developer-id-cert@^1.0"]
    assert body["steps"][3]["sources"][0]["url"].startswith("https://")
    assert body["yaml"].startswith("schema_version: 1")


def test_unknown_playbook_is_404(client: TestClient) -> None:
    response = client.get("/api/v1/playbook", params={"source": "@org/nope"})
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "not_found"


def test_asset_content_is_readable(client: TestClient) -> None:
    response = client.get(
        "/api/v1/playbook/asset",
        params={"source": MAIN, "path": "assets/verify-signatures.sh"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["encoding"] == "utf-8"
    assert "codesign --verify" in body["content"]


def test_unknown_asset_is_404(client: TestClient) -> None:
    response = client.get("/api/v1/playbook/asset", params={"source": MAIN, "path": "assets/nope"})
    assert response.status_code == 404


def test_validate_reports_issues_without_4xx(client: TestClient) -> None:
    body = client.post("/api/v1/validate", json={"playbook_yaml": "schema_version: 1\n"}).json()
    assert body["ok"] is False
    assert body["issues"]


def test_validate_accepts_a_good_playbook(client: TestClient) -> None:
    yaml_text = (
        REPO_ROOT / "playbooks/speccify/apple-developer-id-cert/1.0.0/playbook.yaml"
    ).read_text(encoding="utf-8")
    body = client.post("/api/v1/validate", json={"playbook_yaml": yaml_text}).json()
    assert body == {"ok": True, "issues": []}
