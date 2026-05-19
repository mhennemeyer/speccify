"""Tests for `POST /api/v1/render`.

Happy path goes against the registry fixture for `@org/button@0.1.1` — the
replay cache has a recorded entry for those exact bytes, so we get a Cache
hit and the same TSX the CLI/MCP would produce. Error paths cover the four
documented error codes (`unknown_target`, `spec_invalid`, `cache_miss`,
`bad_request`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
LLM_CACHE = REPO_ROOT / "tests" / "fixtures" / "llm-cache"
BUTTON_YAML_PATH = REGISTRY_FIXTURES / "org" / "button" / "0.1.1" / "spec.speccify.yaml"


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        project_root=REPO_ROOT,
        registry_path=REGISTRY_FIXTURES,
        cache_dir=LLM_CACHE,
    )
    return TestClient(create_app(settings=settings))


@pytest.fixture
def button_yaml() -> str:
    return BUTTON_YAML_PATH.read_text(encoding="utf-8")


def test_render_button_happy_path(client: TestClient, button_yaml: str) -> None:
    response = client.post(
        "/api/v1/render",
        json={
            "spec_id": "@org/button",
            "version": "0.1.1",
            "spec_yaml": button_yaml,
            "target": "react",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["spec_id"] == "@org/button"
    assert body["target"] == "react"
    assert body["files"], "render must return at least one file"
    for rel_path, content in body["files"].items():
        assert rel_path.endswith(".tsx")
        assert isinstance(content, str) and content.strip()
    pin = body["generator_pin"]
    assert pin is not None
    assert pin["kind"] == "llm"
    assert pin["cache_key"].startswith("sha256:")


def test_render_unknown_target_returns_400(client: TestClient, button_yaml: str) -> None:
    response = client.post(
        "/api/v1/render",
        json={
            "spec_id": "@org/button",
            "version": "0.1.1",
            "spec_yaml": button_yaml,
            "target": "swiftui",
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error_code"] == "unknown_target"


def test_render_invalid_yaml_returns_400(client: TestClient) -> None:
    response = client.post(
        "/api/v1/render",
        json={
            "spec_id": "@org/button",
            "version": "0.1.1",
            "spec_yaml": "kind: component\n  bad-indent: [\n",
            "target": "react",
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error_code"] == "spec_invalid"


def test_render_edited_spec_returns_422_cache_miss(client: TestClient, button_yaml: str) -> None:
    edited = button_yaml + "\n# tweak that changes the bytes\n"
    response = client.post(
        "/api/v1/render",
        json={
            "spec_id": "@org/button",
            "version": "0.1.1",
            "spec_yaml": edited,
            "target": "react",
        },
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error_code"] == "cache_miss"
    assert "record_llm_cache" in detail["hint"]


def test_render_bad_version_returns_400(client: TestClient, button_yaml: str) -> None:
    response = client.post(
        "/api/v1/render",
        json={
            "spec_id": "@org/button",
            "version": "not-a-semver",
            "spec_yaml": button_yaml,
            "target": "react",
        },
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error_code"] == "bad_request"
