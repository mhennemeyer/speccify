"""Tests für die Composer-Routen (P3): Detail, Validate, Save."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES = REPO_ROOT / "registry-fixtures"


def _client(registry_path: Path | None = None) -> TestClient:
    settings = Settings(
        project_root=REPO_ROOT,
        registry_path=registry_path or FIXTURES,
        cache_dir=REPO_ROOT / "tests" / "fixtures" / "llm-cache",
    )
    return TestClient(create_app(settings))


def _search_bar_yaml() -> str:
    path = FIXTURES / "org" / "search-bar" / "0.1.0" / "spec.speccify.yaml"
    return path.read_text(encoding="utf-8")


# --- GET /api/v1/specs/{scope}/{name} ----------------------------------------


def test_spec_detail_returns_contract_and_children() -> None:
    response = _client().get("/api/v1/specs/org/search-bar")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == "@org/search-bar"
    assert body["kind"] == "ui-component"
    prop_names = [p["name"] for p in body["api"]["props"]]
    assert prop_names == ["placeholder", "busy"]
    assert body["api"]["props"][0]["mapTo"] == "query_input.placeholder"
    assert body["composition"]["uses"]["go_button"].startswith("@org/button")
    # Kind-Contracts sind aufgelöst mitgeliefert (Canvas/Wiring-Dropdowns).
    assert set(body["children"]) == {"query_input", "go_button"}
    button_api = body["children"]["go_button"]["api"]
    variant = next(p for p in button_api["props"] if p["name"] == "variant")
    assert variant["type"]["kind"] == "enum"
    assert variant["type"]["enumValues"] == ["primary", "secondary", "ghost"]


def test_spec_detail_leaf_has_empty_children() -> None:
    response = _client().get("/api/v1/specs/org/button", params={"version": "0.1.0"})
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "0.1.0"
    assert body["composition"] is None
    assert body["children"] == {}
    assert "0.1.1" in body["versions"]


def test_spec_detail_unknown_is_404() -> None:
    response = _client().get("/api/v1/specs/org/nope")
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "not_found"


# --- POST /api/v1/validate ----------------------------------------------------


def test_validate_ok_for_reference_composite() -> None:
    response = _client().post("/api/v1/validate", json={"spec_yaml": _search_bar_yaml()})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "issues": []}


def test_validate_reports_schema_and_composition_issues() -> None:
    broken = _search_bar_yaml().replace("emit: submitted", "emit: exploded")
    response = _client().post("/api/v1/validate", json={"spec_yaml": broken})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert any(
        issue["source"] == "composition" and "exploded" in issue["message"]
        for issue in body["issues"]
    )


def test_validate_reports_yaml_parse_error() -> None:
    response = _client().post("/api/v1/validate", json={"spec_yaml": "id: [broken"})
    body = response.json()
    assert body["ok"] is False
    assert body["issues"][0]["source"] == "yaml"


# --- POST /api/v1/specs (Save) ------------------------------------------------


def test_save_writes_spec_into_registry(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    shutil.copytree(FIXTURES, registry)
    client = _client(registry)

    new_yaml = (
        _search_bar_yaml()
        .replace("@org/search-bar", "@org/hero-search")
        .replace('id: "@org/hero-search"', 'id: "@org/hero-search"')
    )
    response = client.post("/api/v1/specs", json={"spec_yaml": new_yaml})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == "@org/hero-search"
    saved = registry / "org" / "hero-search" / "0.1.0" / "spec.speccify.yaml"
    assert saved.is_file()

    # Rekursive Komposition: die gespeicherte Spec ist sofort im Detail abrufbar.
    detail = client.get("/api/v1/specs/org/hero-search").json()
    assert detail["id"] == "@org/hero-search"
    assert set(detail["children"]) == {"query_input", "go_button"}
    # … und mockbar (Composer-Palette-Pfad).
    mock = client.post("/api/v1/mock", json={"spec_id": "@org/hero-search"})
    assert mock.status_code == 200
    assert "org/HeroSearch.mock.tsx" in mock.json()["files"]


def test_save_rejects_invalid_spec_with_issues(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    shutil.copytree(FIXTURES, registry)
    broken = _search_bar_yaml().replace("kind: ui-component", "kind: gadget")
    response = _client(registry).post("/api/v1/specs", json={"spec_yaml": broken})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error_code"] == "validation_failed"
    assert any(issue["source"] == "schema" for issue in detail["issues"])
