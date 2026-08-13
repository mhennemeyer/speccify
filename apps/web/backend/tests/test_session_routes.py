"""Tests for the viewer/agent bridge: selection and proposals."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app
from speccify_web_backend.routes.session import reset_state
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[4]
MAIN = "@speccify/macos-notarize-tauri"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """A client over a throwaway copy of the library — proposals write to disk."""
    library = tmp_path / "skills"
    shutil.copytree(REPO_ROOT / "skills", library)
    reset_state()
    settings = Settings(project_root=REPO_ROOT, library_path=library)
    return TestClient(create_app(settings))


def _markdown(client: TestClient) -> str:
    return client.get("/api/v1/skill", params={"source": MAIN}).json()["raw"]


def test_selection_is_empty_until_the_viewer_pushes(client: TestClient) -> None:
    assert client.get("/api/v1/selection").json() == {"selection": {}}


def test_step_selection_comes_back_resolved(client: TestClient) -> None:
    """The agent should not need three more calls to learn what was clicked."""
    client.put(
        "/api/v1/selection",
        json={
            "source": MAIN,
            "kind": "step",
            "step_title": "Submit to notarytool and wait for the verdict",
        },
    )
    selection = client.get("/api/v1/selection").json()["selection"]
    assert selection["skill"]["id"] == MAIN
    assert selection["step"]["number"] == 4
    assert "notarytool submit" in selection["step"]["body"]


def test_file_selection_carries_the_content(client: TestClient) -> None:
    client.put(
        "/api/v1/selection",
        json={"source": MAIN, "kind": "file", "file_path": "assets/verify-signatures.sh"},
    )
    selection = client.get("/api/v1/selection").json()["selection"]
    assert "codesign --verify" in selection["file"]["content"]


def test_source_selection_carries_its_age(client: TestClient) -> None:
    url = client.get("/api/v1/skill", params={"source": MAIN}).json()["sources"][0]["url"]
    client.put("/api/v1/selection", json={"source": MAIN, "kind": "source", "source_url": url})
    selection = client.get("/api/v1/selection").json()["selection"]
    assert selection["source_entry"]["retrieved"] == "2026-08-06"


def test_proposal_round_trip_writes_only_on_apply(client: TestClient) -> None:
    original = _markdown(client)
    changed = original.replace(
        "## Pitfalls\n",
        "## Pitfalls\n\n- Stapling a .dmg is not the same as stapling the .app inside it.\n",
    )
    assert changed != original

    posted = client.post(
        "/api/v1/proposal",
        json={"source": MAIN, "skill_markdown": changed, "rationale": "One more pitfall."},
    )
    assert posted.status_code == 200, posted.text

    # Waiting, not written.
    pending = client.get("/api/v1/proposal").json()["proposal"]
    assert pending["rationale"] == "One more pitfall."
    assert _markdown(client) == original

    applied = client.post("/api/v1/proposal/apply")
    assert applied.status_code == 200, applied.text
    assert "Stapling a .dmg" in _markdown(client)
    # The proposal is consumed.
    assert client.get("/api/v1/proposal").json()["proposal"] == {}


def test_a_broken_proposal_never_becomes_a_diff(client: TestClient) -> None:
    """An invalid skill would be a diff the user cannot apply."""
    response = client.post(
        "/api/v1/proposal",
        json={"source": MAIN, "skill_markdown": "---\nname: Not-Valid\ndescription: x\n---\n"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "invalid_skill"
    assert client.get("/api/v1/proposal").json()["proposal"] == {}


def test_style_findings_ride_along_instead_of_blocking(client: TestClient) -> None:
    """A weak description is worth seeing, but it is not a reason to refuse."""
    weak = _markdown(client).replace(
        "description:", "description: Notarizes things.\nx-original-description:", 1
    )
    posted = client.post("/api/v1/proposal", json={"source": MAIN, "skill_markdown": weak})
    assert posted.status_code == 200, posted.text
    pending = client.get("/api/v1/proposal").json()["proposal"]
    assert any(finding["level"] == "warning" for finding in pending["findings"])


def test_discarding_clears_the_proposal(client: TestClient) -> None:
    client.post(
        "/api/v1/proposal",
        json={"source": MAIN, "skill_markdown": _markdown(client), "rationale": "noop"},
    )
    client.delete("/api/v1/proposal")
    assert client.get("/api/v1/proposal").json()["proposal"] == {}


def test_applying_without_a_proposal_is_404(client: TestClient) -> None:
    assert client.post("/api/v1/proposal/apply").status_code == 404


def test_git_sourced_skills_cannot_be_written(client: TestClient) -> None:
    """Editing someone else's repository through the viewer would be wrong."""
    client.post(
        "/api/v1/proposal",
        json={"source": "git+https://example.com/repo", "skill_markdown": _markdown(client)},
    )
    response = client.post("/api/v1/proposal/apply")
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "not_local"
