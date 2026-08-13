"""Tools that connect an agent to the viewer the user is looking at.

The viewer pushes its selection to the backend; these tools read it. That is
what makes "why is this necessary?" resolve against the step on screen instead
of requiring the user to restate it.

Talking to the backend over HTTP is deliberate: the selection lives in the
process that serves the viewer, and the MCP server is a separate process. The
base URL comes from `SPECCIFY_API` (default `http://127.0.0.1:8000`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

API_ENV = "SPECCIFY_API"
DEFAULT_API = "http://127.0.0.1:8000"
TIMEOUT = 10.0


def api_base() -> str:
    return os.environ.get(API_ENV, DEFAULT_API).rstrip("/")


@dataclass(frozen=True)
class ViewerResult:
    ok: bool
    selection: dict[str, Any] = field(default_factory=dict)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "selection": dict(self.selection),
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True)
class ProposalResult:
    ok: bool
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "code": self.code, "message": self.message}


def _unreachable(exc: Exception) -> str:
    return (
        f"The Speccify backend at {api_base()} is not reachable ({type(exc).__name__}). "
        f"Start it with `./scripts/dev-up.sh`, or set {API_ENV} if it runs elsewhere."
    )


def run_viewer_selection() -> ViewerResult:
    """What the user currently has selected in the viewer, resolved."""
    import httpx

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(f"{api_base()}/api/v1/selection")
            response.raise_for_status()
            selection = response.json().get("selection") or {}
    except Exception as exc:  # noqa: BLE001 - reported as a structured result
        return ViewerResult(ok=False, code="backend_unreachable", message=_unreachable(exc))

    if not selection:
        return ViewerResult(
            ok=True,
            selection={},
            message="Nothing is selected in the viewer right now.",
        )
    return ViewerResult(ok=True, selection=selection)


def run_skill_propose(
    *,
    source: str,
    skill_markdown: str,
    rationale: str = "",
) -> ProposalResult:
    """Offer a changed skill to the user; they apply it, not you."""
    import httpx

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                f"{api_base()}/api/v1/proposal",
                json={
                    "source": source,
                    "skill_markdown": skill_markdown,
                    "rationale": rationale,
                },
            )
    except Exception as exc:  # noqa: BLE001 - reported as a structured result
        return ProposalResult(ok=False, code="backend_unreachable", message=_unreachable(exc))

    if response.status_code == 422:
        detail = response.json().get("detail", {})
        return ProposalResult(
            ok=False,
            code=str(detail.get("error_code", "invalid_skill")),
            message=str(detail.get("message", "The proposed playbook is not valid.")),
        )
    if response.status_code >= 400:
        return ProposalResult(
            ok=False, code="rejected", message=f"The backend answered {response.status_code}."
        )
    return ProposalResult(
        ok=True,
        message="Proposal is waiting in the viewer — the user decides whether to apply it.",
    )
