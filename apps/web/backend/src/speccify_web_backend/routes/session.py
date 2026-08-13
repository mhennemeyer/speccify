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

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from speccify_core import (
    LibraryError,
    parse_uses_entry,
)
from speccify_core.skill import SKILL_FILENAME, SkillError, parse_skill
from speccify_core.skill_check import check_skill
from speccify_core.skill_library import LocalSkillLibrary

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
    kind: str = Field("skill", description="skill | step | source | file")
    step_title: str | None = None
    source_url: str | None = None
    file_path: str | None = None


class ProposalPayload(BaseModel):
    source: str = Field(..., description="playbook the proposal applies to")
    skill_markdown: str = Field(..., description="the full proposed SKILL.md")
    rationale: str = Field("", description="one or two sentences: what changed and why")


def _resolve_selection(request: Request, selection: dict[str, Any]) -> dict[str, Any]:
    """Fill a raw selection with what it actually points at.

    The agent should not have to make three more calls to learn which step the
    user clicked and what it says.
    """
    if not selection:
        return {}
    resolved = dict(selection)
    try:
        library = request.app.state.settings.library()
        skill_id, _ = parse_uses_entry(selection["source"])
        versions = library.list_versions(skill_id)
        if not versions:
            return resolved
        bundle = library.fetch(skill_id, versions[-1])
        skill = bundle.skill()
    except (LibraryError, ValueError, KeyError):
        return resolved

    resolved["skill"] = {
        "id": skill.qualified_id,
        "version": skill.version,
        "description": skill.description,
    }
    kind = selection.get("kind")
    if kind == "step" and selection.get("step_title"):
        wanted = str(selection["step_title"])
        step = next((s for s in skill.steps if s.title == wanted), None)
        if step is not None:
            resolved["step"] = {
                "number": step.number,
                "title": step.title,
                "body": step.body,
                "verify": step.verify,
            }
    elif kind == "source" and selection.get("source_url"):
        wanted = str(selection["source_url"])
        source = next((s for s in skill.sources if s.url == wanted), None)
        if source is not None:
            resolved["source_entry"] = {
                "title": source.title,
                "url": source.url,
                "retrieved": source.retrieved,
            }
    elif kind == "file" and selection.get("file_path"):
        data = bundle.files.get(str(selection["file_path"]))
        if data is not None:
            try:
                resolved["file"] = {
                    "path": selection["file_path"],
                    "content": data.decode("utf-8"),
                }
            except UnicodeDecodeError:
                resolved["file"] = {"path": selection["file_path"], "content": None}
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
    """An agent proposes a changed skill. Validated, never written.

    Only specification errors block: a proposal that cannot be applied must
    not become a diff on screen. Style findings ride along so the human sees
    them next to the change instead of after it.
    """
    try:
        skill = parse_skill(payload.skill_markdown)
    except SkillError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "invalid_skill", "message": str(exc)},
        ) from exc

    findings = check_skill(skill)
    errors = [f for f in findings if f.is_error]
    if errors:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "invalid_skill",
                "message": "; ".join(f.format() for f in errors[:5]),
            },
        )

    state().proposal = {
        "source": payload.source,
        "skill_markdown": payload.skill_markdown,
        "rationale": payload.rationale,
        "findings": [{"level": f.level, "path": f.path, "message": f.message} for f in findings],
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
    skill_id, _ = parse_uses_entry(str(proposal["source"]))
    if skill_id.startswith("git+"):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "not_local",
                "message": (
                    "This skill comes from a git source. Changes belong in that "
                    "repository — clone it, apply there, tag a new version."
                ),
            },
        )
    try:
        library = LocalSkillLibrary(settings.library_path)
        if not library.list_versions(skill_id):
            raise LibraryError(f"'{skill_id}' is not in the local library.")
    except LibraryError as exc:
        raise HTTPException(
            status_code=404, detail={"error_code": "not_found", "message": str(exc)}
        ) from exc

    # `name` is the directory; the scope lives in the file, not the path.
    name = skill_id.rsplit("/", 1)[-1]
    target = settings.library_path / name / SKILL_FILENAME
    target.write_text(proposal["skill_markdown"], encoding="utf-8")
    state().proposal = {}
    return {"ok": True, "path": str(target)}
