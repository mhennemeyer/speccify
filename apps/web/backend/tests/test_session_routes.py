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
    library = tmp_path / "playbooks"
    shutil.copytree(REPO_ROOT / "playbooks", library)
    reset_state()
    settings = Settings(
        project_root=REPO_ROOT,
        library_path=library,
    )
    return TestClient(create_app(settings))


def test_selection_is_empty_until_the_viewer_pushes(client: TestClient) -> None:
    assert client.get("/api/v1/selection").json() == {"selection": {}}


def test_step_selection_comes_back_resolved(client: TestClient) -> None:
    """The agent should not need three more calls to learn what was clicked."""
    client.put(
        "/api/v1/selection",
        json={"source": MAIN, "kind": "step", "step_id": "notarize"},
    )
    selection = client.get("/api/v1/selection").json()["selection"]
    assert selection["playbook"]["id"] == MAIN
    assert selection["step"]["title"].startswith("Submit to notarytool")
    assert selection["step"]["sources"][0]["url"].startswith("https://")


def test_asset_selection_carries_the_content(client: TestClient) -> None:
    client.put(
        "/api/v1/selection",
        json={"source": MAIN, "kind": "asset", "asset_path": "assets/verify-signatures.sh"},
    )
    selection = client.get("/api/v1/selection").json()["selection"]
    assert "codesign --verify" in selection["asset"]["content"]


def test_source_selection_carries_the_link(client: TestClient) -> None:
    client.put(
        "/api/v1/selection",
        json={"source": MAIN, "kind": "source", "source_id": "notarytool_docs"},
    )
    selection = client.get("/api/v1/selection").json()["selection"]
    assert selection["source_entry"]["retrieved"] == "2026-08-06"


def _playbook_yaml(client: TestClient) -> str:
    return client.get("/api/v1/playbook", params={"source": MAIN}).json()["yaml"]


def test_proposal_round_trip_writes_only_on_apply(client: TestClient, tmp_path: Path) -> None:
    original = _playbook_yaml(client)
    addition = "  - Stapling a .dmg is not the same as stapling the .app inside it."
    changed = original.replace("pitfalls:", f"pitfalls:\n{addition}")

    assert (
        client.post(
            "/api/v1/proposal",
            json={"source": MAIN, "playbook_yaml": changed, "rationale": "One more pitfall."},
        ).status_code
        == 200
    )

    # Waiting, not written.
    pending = client.get("/api/v1/proposal").json()["proposal"]
    assert pending["rationale"] == "One more pitfall."
    assert _playbook_yaml(client) == original

    applied = client.post("/api/v1/proposal/apply")
    assert applied.status_code == 200, applied.text
    assert "Stapling a .dmg" in _playbook_yaml(client)
    # The proposal is consumed.
    assert client.get("/api/v1/proposal").json()["proposal"] == {}


def test_invalid_proposal_is_rejected_with_the_reason(client: TestClient) -> None:
    response = client.post(
        "/api/v1/proposal",
        json={"source": MAIN, "playbook_yaml": "schema_version: 1\nid: nonsense\n"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "invalid_playbook"
    assert client.get("/api/v1/proposal").json()["proposal"] == {}


def test_discarding_clears_the_proposal(client: TestClient) -> None:
    client.post(
        "/api/v1/proposal",
        json={"source": MAIN, "playbook_yaml": _playbook_yaml(client), "rationale": "noop"},
    )
    client.delete("/api/v1/proposal")
    assert client.get("/api/v1/proposal").json()["proposal"] == {}


def test_applying_without_a_proposal_is_404(client: TestClient) -> None:
    assert client.post("/api/v1/proposal/apply").status_code == 404


def test_git_sourced_playbooks_cannot_be_written(client: TestClient) -> None:
    """Editing someone else's repository through the viewer would be wrong."""
    yaml_text = _playbook_yaml(client)
    client.post(
        "/api/v1/proposal",
        json={"source": "git+https://example.com/repo", "playbook_yaml": yaml_text},
    )
    response = client.post("/api/v1/proposal/apply")
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "not_local"
