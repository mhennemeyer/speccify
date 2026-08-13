"""Tests for the skill HTTP routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS = REPO_ROOT / "skills"
MAIN = "@speccify/macos-notarize-tauri"


@pytest.fixture
def client() -> TestClient:
    settings = Settings(project_root=REPO_ROOT, library_path=SKILLS)
    return TestClient(create_app(settings))


def test_list_skills_is_shallow(client: TestClient) -> None:
    """The list is for choosing; the markdown belongs to the detail call."""
    body = client.get("/api/v1/skills").json()
    entries = {entry["id"]: entry for entry in body["skills"]}
    assert MAIN in entries
    assert "tauri" in entries[MAIN]["stack"]
    assert "markdown" not in entries[MAIN]


def test_get_skill_leads_with_the_markdown(client: TestClient) -> None:
    response = client.get("/api/v1/skill", params={"source": MAIN})
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["version"] == "1.0.0"
    assert "hardened runtime" in body["markdown"]
    assert body["uses"] == ["@speccify/apple-developer-id-cert@^1.0"]
    assert [step["number"] for step in body["steps"]] == [1, 2, 3, 4, 5]
    assert body["sources"][0]["url"].startswith("https://")
    # The raw file, so the proposal panel can diff against it.
    assert body["raw"].startswith("---")


def test_unknown_skill_is_404(client: TestClient) -> None:
    response = client.get("/api/v1/skill", params={"source": "@org/nope"})
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "not_found"


def test_bundled_file_is_readable(client: TestClient) -> None:
    response = client.get(
        "/api/v1/skill/file",
        params={"source": MAIN, "path": "assets/verify-signatures.sh"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["encoding"] == "utf-8"
    assert "codesign --verify" in body["content"]


def test_unknown_file_is_404(client: TestClient) -> None:
    response = client.get("/api/v1/skill/file", params={"source": MAIN, "path": "assets/nope"})
    assert response.status_code == 404


def test_validate_reports_findings_without_4xx(client: TestClient) -> None:
    """Content problems are findings, not transport errors."""
    body = client.post(
        "/api/v1/validate", json={"skill_markdown": "---\nname: Not-Valid\ndescription: x\n---\n"}
    ).json()
    assert body["ok"] is False
    assert any(finding["level"] == "error" for finding in body["findings"])


def test_validate_separates_style_from_breakage(client: TestClient) -> None:
    """A description that never says *when* is a warning, not a rejection."""
    body = client.post(
        "/api/v1/validate",
        json={"skill_markdown": "---\nname: a-skill\ndescription: Processes PDFs.\n---\n"},
    ).json()
    assert body["ok"] is True
    assert [finding["level"] for finding in body["findings"]] == ["warning"]


def test_validate_accepts_a_shipped_skill(client: TestClient) -> None:
    markdown = (SKILLS / "apple-developer-id-cert" / "SKILL.md").read_text(encoding="utf-8")
    body = client.post("/api/v1/validate", json={"skill_markdown": markdown}).json()
    assert body == {"ok": True, "findings": []}
