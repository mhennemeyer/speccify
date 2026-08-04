"""Tests für `POST /api/v1/build` (P4) inkl. Cross-Consistency CLI ↔ MCP ↔ Web."""

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


def test_build_returns_a_complete_project() -> None:
    response = _client().post("/api/v1/build", json={"spec_id": "@org/demo-app"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == "0.1.0"
    assert body["template_set"] == "p4-app-react"
    assert body["mocks"] is True
    assert {"index.html", "package.json", "src/App.tsx", "src/router.tsx"} <= set(body["files"])
    assert 'navigate("/suche")' in body["files"]["src/App.tsx"]


def test_build_rejects_component_specs() -> None:
    response = _client().post("/api/v1/build", json={"spec_id": "@org/button"})
    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "build_failed"


def test_build_unknown_spec_is_404() -> None:
    response = _client().post("/api/v1/build", json={"spec_id": "@org/nope"})
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "not_found"


def test_build_unknown_target_is_400() -> None:
    response = _client().post(
        "/api/v1/build", json={"spec_id": "@org/demo-app", "target": "swiftui"}
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "unknown_target"


def test_build_cross_consistency_cli_mcp_web(tmp_path: Path) -> None:
    """Alle drei Adapter schreiben byte-identische Projekt-Dateien (D15)."""
    from speccify_cli.commands.build import run_build as cli_run_build
    from speccify_mcp.tools.build import run_build as mcp_run_build

    cli_result = cli_run_build(
        "@org/demo-app",
        registry_path=REPO_ROOT / "registry-fixtures",
        out_dir=tmp_path / "cli-app",
    )
    mcp_result = mcp_run_build(
        REPO_ROOT,
        spec_ref="@org/demo-app",
        out_dir=tmp_path / "mcp-app",
    )
    web_body = _client().post("/api/v1/build", json={"spec_id": "@org/demo-app"}).json()

    assert mcp_result.ok, mcp_result.message
    assert sorted(web_body["files"]) == sorted(cli_result.files) == mcp_result.files
    for rel_path, cli_bytes in cli_result.files.items():
        assert web_body["files"][rel_path] == cli_bytes.decode("utf-8"), rel_path
        assert (tmp_path / "cli-app" / rel_path).read_bytes() == cli_bytes, rel_path
        assert (tmp_path / "mcp-app" / rel_path).read_bytes() == cli_bytes, rel_path
