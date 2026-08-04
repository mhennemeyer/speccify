"""Tests für `POST /api/v1/mock` (+ `/mock/draft`, P3) inkl. Cross-Consistency zum CLI-Pfad."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]


def _client() -> TestClient:
    settings = Settings(
        project_root=REPO_ROOT,
        registry_path=REPO_ROOT / "registry-fixtures",
        cache_dir=REPO_ROOT / "tests" / "fixtures" / "llm-cache",
    )
    return TestClient(create_app(settings))


def test_mock_returns_closure_files() -> None:
    response = _client().post("/api/v1/mock", json={"spec_id": "@org/search-bar"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == "0.1.0"
    assert sorted(body["files"]) == [
        "org/Button.mock.tsx",
        "org/SearchBar.mock.tsx",
        "org/TextInput.mock.tsx",
    ]
    assert body["template_set"] == "p2-mock-react"
    assert body["entry"] == "org/SearchBar.mock.tsx"
    assert "export default function SearchBar" in body["files"]["org/SearchBar.mock.tsx"]


def test_mock_unknown_target_is_400() -> None:
    response = _client().post("/api/v1/mock", json={"spec_id": "@org/button", "target": "swiftui"})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "unknown_target"


def test_mock_unknown_spec_is_404() -> None:
    response = _client().post("/api/v1/mock", json={"spec_id": "@org/nope"})
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "not_found"


def test_mock_draft_matches_saved_spec_bytes() -> None:
    """Entwurfs-Mock == Registry-Mock derselben Spec (der Composer sieht den echten Output)."""
    client = _client()
    spec_yaml = (
        REPO_ROOT / "registry-fixtures" / "org" / "search-bar" / "0.1.0" / "spec.speccify.yaml"
    ).read_text(encoding="utf-8")

    draft = client.post("/api/v1/mock/draft", json={"spec_yaml": spec_yaml})
    assert draft.status_code == 200, draft.text
    saved = client.post("/api/v1/mock", json={"spec_id": "@org/search-bar"}).json()

    body = draft.json()
    assert body["entry"] == "org/SearchBar.mock.tsx"
    assert body["files"] == saved["files"]


def test_mock_draft_renders_unsaved_composite() -> None:
    """Ein noch nie gespeichertes Composite ist mockbar — Kinder kommen aus der Registry."""
    spec_yaml = (
        "schema_version: 1\n"
        "id: '@org/draft-widget'\n"
        "version: 0.1.0\n"
        "kind: ui-component\n"
        "title: Draft Widget\n"
        "summary: Ungespeicherter Entwurf aus dem Composer.\n"
        "api:\n"
        "  props: []\n"
        "  events: []\n"
        "composition:\n"
        "  uses:\n"
        "    btn: '@org/button@0.1.0'\n"
        "  tree:\n"
        "    - node: btn\n"
        "      props:\n"
        "        label: Los\n"
    )
    response = _client().post("/api/v1/mock/draft", json={"spec_yaml": spec_yaml})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["entry"] == "org/DraftWidget.mock.tsx"
    assert sorted(body["files"]) == ["org/Button.mock.tsx", "org/DraftWidget.mock.tsx"]
    assert 'import Button from "./Button.mock"' in body["files"]["org/DraftWidget.mock.tsx"]


def test_mock_draft_unresolvable_child_is_404() -> None:
    spec_yaml = (
        "schema_version: 1\n"
        "id: '@org/draft-widget'\n"
        "version: 0.1.0\n"
        "kind: ui-component\n"
        "title: Draft Widget\n"
        "summary: Kind existiert nicht.\n"
        "api:\n"
        "  props: []\n"
        "composition:\n"
        "  uses:\n"
        "    ghost: '@org/nope@0.1.0'\n"
        "  tree:\n"
        "    - node: ghost\n"
    )
    response = _client().post("/api/v1/mock/draft", json={"spec_yaml": spec_yaml})
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "not_found"


def test_mock_draft_without_id_is_400() -> None:
    response = _client().post("/api/v1/mock/draft", json={"spec_yaml": "kind: ui-component\n"})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "bad_request"


def test_mock_cross_consistency_web_vs_cli(tmp_path: Path) -> None:
    """Web-Mock-Bytes == CLI-Mock-Bytes (Cross-Consistency-Vertrag, Mock-Pfad)."""
    from speccify_cli.commands.mock import run_mock as cli_run_mock

    cli_result = cli_run_mock(
        "@org/search-bar",
        registry_path=REPO_ROOT / "registry-fixtures",
        out_dir=tmp_path / "cli-mocks",
    )
    web_body = _client().post("/api/v1/mock", json={"spec_id": "@org/search-bar"}).json()
    assert sorted(web_body["files"]) == sorted(cli_result.files)
    for rel_path, cli_bytes in cli_result.files.items():
        assert web_body["files"][rel_path] == cli_bytes.decode("utf-8"), rel_path
