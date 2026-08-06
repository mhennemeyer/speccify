"""The bridge between the viewer and the agent sitting next to it.

Two pieces of shared state, both deliberately in memory:

* **selection** — what the user clicked. The viewer pushes it, the agent reads
  it through the `viewer_selection` MCP tool. That is what makes "why is this
  necessary?" resolve against the step on screen without restating it.
* **proposal** — a changed playbook the agent suggests. The viewer shows it as
  a diff with an Apply button; nothing is written until a human says so.

In memory on purpose: this is one person, one viewer, one agent, on one
machine. Persisting it would mean stale selections outliving the session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from speccify_core import (
    PLAYBOOK_FILENAME,
    LibraryError,
    LocalLibrary,
    Version,
    parse_playbook,
    parse_uses_entry,
    validate_playbook,
)

router = APIRouter(prefix="/api/v1", tags=["session"])


@dataclass
class SessionState:
    """What the viewer and the agent share for the length of a session."""

    selection: dict[str, Any] = field(default_factory=dict)
    proposal: dict[str, Any] = field(default_factory=dict)


_STATE = SessionState()


def state() -> SessionState:
    return _STATE


def reset_state() -> None:
    """Only used by tests — the process-wide state would leak between them."""
    _STATE.selection = {}
    _STATE.proposal = {}


class SelectionPayload(BaseModel):
    source: str = Field(..., description="playbook id or git source currently open")
    kind: str = Field("playbook", description="playbook | step | source | asset")
    step_id: str | None = None
    source_id: str | None = None
    asset_path: str | None = None


class ProposalPayload(BaseModel):
    source: str = Field(..., description="playbook the proposal applies to")
    playbook_yaml: str = Field(..., description="the full proposed playbook.yaml")
    rationale: str = Field("", description="one or two sentences: what changed and why")


def _resolve_selection(request: Request, selection: dict[str, Any]) -> dict[str, Any]:
    """Fill a raw selection with what it actually points at.

    The agent should not have to make three more calls to learn that the user
    clicked step `notarize` and what that step says.
    """
    if not selection:
        return {}
    resolved = dict(selection)
    try:
        library = request.app.state.settings.library()
        playbook_id, _ = parse_uses_entry(selection["source"])
        versions = library.list_versions(playbook_id)
        if not versions:
            return resolved
        bundle = library.fetch(playbook_id, versions[-1])
        playbook = parse_playbook(bundle.parsed())
    except (LibraryError, ValueError, KeyError):
        return resolved

    resolved["playbook"] = {
        "id": playbook.id,
        "version": playbook.version,
        "title": playbook.title,
        "summary": playbook.summary,
    }
    kind = selection.get("kind")
    if kind == "step" and selection.get("step_id"):
        step = playbook.step(str(selection["step_id"]))
        if step is not None:
            resolved["step"] = {
                "id": step.id,
                "title": step.title,
                "detail": step.detail,
                "uses": step.uses,
                "verify": step.verify,
                "assets": list(step.assets),
                "sources": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "url": s.url,
                        "retrieved": s.retrieved,
                    }
                    for s in (playbook.source(sid) for sid in step.sources)
                    if s is not None
                ],
            }
    elif kind == "source" and selection.get("source_id"):
        source = playbook.source(str(selection["source_id"]))
        if source is not None:
            resolved["source_entry"] = {
                "id": source.id,
                "title": source.title,
                "url": source.url,
                "retrieved": source.retrieved,
                "note": source.note,
            }
    elif kind == "asset" and selection.get("asset_path"):
        data = bundle.files.get(str(selection["asset_path"]))
        if data is not None:
            try:
                resolved["asset"] = {
                    "path": selection["asset_path"],
                    "content": data.decode("utf-8"),
                }
            except UnicodeDecodeError:
                resolved["asset"] = {"path": selection["asset_path"], "content": None}
    return resolved


@router.put("/selection")
def put_selection(payload: SelectionPayload) -> dict[str, Any]:
    """The viewer pushes what the user clicked."""
    state().selection = payload.model_dump(exclude_none=True)
    return {"ok": True, "selection": state().selection}


@router.get("/selection")
def get_selection(request: Request) -> dict[str, Any]:
    """What the user is looking at, resolved — this is what the agent reads."""
    return {"selection": _resolve_selection(request, state().selection)}


@router.post("/proposal")
def post_proposal(payload: ProposalPayload, request: Request) -> dict[str, Any]:
    """An agent proposes a changed playbook. Validated, never written."""
    try:
        data = yaml.safe_load(payload.playbook_yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "invalid_yaml", "message": str(exc)},
        ) from exc

    issues = validate_playbook(data)
    if issues:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "invalid_playbook",
                "message": "; ".join(issue.format() for issue in issues[:5]),
            },
        )

    state().proposal = {
        "source": payload.source,
        "playbook_yaml": payload.playbook_yaml,
        "rationale": payload.rationale,
    }
    return {"ok": True, "message": "Proposal is waiting for the user to apply it."}


@router.get("/proposal")
def get_proposal() -> dict[str, Any]:
    """The viewer polls for a pending proposal."""
    return {"proposal": state().proposal}


@router.delete("/proposal")
def discard_proposal() -> dict[str, Any]:
    state().proposal = {}
    return {"ok": True}


@router.post("/proposal/apply")
def apply_proposal(request: Request) -> dict[str, Any]:
    """Write the pending proposal to the local library. Only a human gets here."""
    proposal = state().proposal
    if not proposal:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "no_proposal", "message": "Nothing to apply."},
        )

    settings = request.app.state.settings
    playbook_id, _ = parse_uses_entry(str(proposal["source"]))
    if playbook_id.startswith("git+"):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "not_local",
                "message": (
                    "This playbook comes from a git source. Changes belong in that "
                    "repository — clone it, apply there, tag a new version."
                ),
            },
        )
    try:
        library = LocalLibrary(settings.library_path)
        versions = library.list_versions(playbook_id)
        if not versions:
            raise LibraryError(f"'{playbook_id}' is not in the local library.")
        version: Version = versions[-1]
    except LibraryError as exc:
        raise HTTPException(
            status_code=404, detail={"error_code": "not_found", "message": str(exc)}
        ) from exc

    scope, name = playbook_id.lstrip("@").split("/", 1)
    target = settings.library_path / scope / name / str(version) / PLAYBOOK_FILENAME
    target.write_text(proposal["playbook_yaml"], encoding="utf-8")
    state().proposal = {}
    return {"ok": True, "path": str(target)}
