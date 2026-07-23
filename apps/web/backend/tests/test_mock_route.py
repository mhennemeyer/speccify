"""Tests für `POST /api/v1/mock` (P2 Stage 5) inkl. Cross-Consistency zum CLI-Pfad."""

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
    assert "export default function SearchBar" in body["files"]["org/SearchBar.mock.tsx"]


def test_mock_unknown_target_is_400() -> None:
    response = _client().post("/api/v1/mock", json={"spec_id": "@org/button", "target": "swiftui"})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "unknown_target"


def test_mock_unknown_spec_is_404() -> None:
    response = _client().post("/api/v1/mock", json={"spec_id": "@org/nope"})
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "not_found"


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
