"""Tests for the viewer bridge tools — against a real backend in-process."""

from __future__ import annotations

import shutil
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn
from speccify_mcp.tools import run_skill_propose, run_viewer_selection
from speccify_mcp.tools.viewer import API_ENV
from speccify_web_backend.app import create_app
from speccify_web_backend.routes.session import reset_state
from speccify_web_backend.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN = "@speccify/macos-notarize-tauri"


@pytest.fixture
def backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """A real backend on a free port — the tools talk HTTP, so a fake would prove less."""
    library = tmp_path / "skills"
    shutil.copytree(REPO_ROOT / "skills", library)
    reset_state()
    app = create_app(Settings(project_root=REPO_ROOT, library_path=library))
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        if not thread.is_alive():  # pragma: no cover - startup failure
            raise RuntimeError("backend did not start")
    port = server.servers[0].sockets[0].getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    monkeypatch.setenv(API_ENV, base)
    try:
        yield base
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _put_selection(base: str, payload: dict) -> None:
    import httpx

    httpx.put(f"{base}/api/v1/selection", json=payload, timeout=10).raise_for_status()


def test_selection_is_empty_and_says_so(backend: str) -> None:
    result = run_viewer_selection()
    assert result.ok
    assert result.selection == {}
    assert "Nothing is selected" in result.message


def test_agent_sees_the_step_the_user_clicked(backend: str) -> None:
    """The whole point of W4: context the user did not have to restate."""
    _put_selection(
        backend,
        {"source": MAIN, "kind": "step", "step_title": "Build with signing enabled"},
    )
    result = run_viewer_selection()
    assert result.ok
    assert result.selection["skill"]["id"] == MAIN
    assert result.selection["step"]["title"] == "Build with signing enabled"
    # Resolved, not just an identifier — the agent gets the text of the step.
    assert "sidecar" in result.selection["step"]["body"]


def test_proposal_reaches_the_viewer(backend: str) -> None:
    import httpx

    current = httpx.get(f"{backend}/api/v1/skill", params={"source": MAIN}, timeout=10).json()[
        "raw"
    ]
    changed = current.replace("pitfalls:", "pitfalls:\n  - Proposed by an agent.")

    result = run_skill_propose(source=MAIN, skill_markdown=changed, rationale="Adding a pitfall.")
    assert result.ok, result.message

    pending = httpx.get(f"{backend}/api/v1/proposal", timeout=10).json()["proposal"]
    assert pending["rationale"] == "Adding a pitfall."
    # Still only a proposal — nothing on disk changed.
    unchanged = httpx.get(f"{backend}/api/v1/skill", params={"source": MAIN}, timeout=10).json()[
        "raw"
    ]
    assert "Proposed by an agent" not in unchanged


def test_broken_proposal_comes_back_with_the_reason(backend: str) -> None:
    result = run_skill_propose(
        source=MAIN, skill_markdown="---\nname: Not-Valid\ndescription: x\n---\n"
    )
    assert not result.ok
    assert result.code == "invalid_skill"
    assert "name" in result.message


def test_unreachable_backend_is_a_structured_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    """An agent must be able to act on this, not crash on it."""
    monkeypatch.setenv(API_ENV, "http://127.0.0.1:9")
    result = run_viewer_selection()
    assert not result.ok
    assert result.code == "backend_unreachable"
    assert "dev-up.sh" in result.message
