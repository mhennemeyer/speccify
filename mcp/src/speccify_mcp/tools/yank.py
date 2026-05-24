"""`yank`-Tool: markiert eine veröffentlichte Spec-Version als geyanked.

Dünner HTTP-Adapter über ``POST /api/v1/registry/specs/<scope>/<name>/<version>/yank``
— spiegelt 1:1 das CLI-Verhalten in ``cli/src/speccify_cli/commands/yank.py``,
gibt jedoch — statt Prozess-Exit-Codes — ein strukturiertes Dict zurück,
damit der MCP-Client (Coding-Agent) programmatisch reagieren kann.

Auth-Token wird aus derselben Credentials-Datei gelesen wie für
``speccify login``; MCP-Server und CLI teilen sich also den Login-State.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import httpx
from speccify_cli import _credentials

# ``@scope/name@version`` reference, e.g. ``@org/button@0.1.0``.
_REF_RE = re.compile(
    r"^@(?P<scope>[a-z0-9][a-z0-9-]*)/(?P<name>[a-z0-9][a-z0-9-]*)@"
    r"(?P<version>(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*))$"
)


@dataclass(frozen=True)
class YankResult:
    """Strukturierter Output des `yank`-Tools.

    - ``ok``: True bei HTTP 200 (frischer Yank oder idempotent).
    - ``already_yanked``: True, wenn die Version vor diesem Aufruf bereits
      geyanked war (Idempotenz-Indikator).
    - ``code``: Server-seitiger Error-Code (`scope_forbidden`,
      `version_not_found`, `stale_2fa`, ...) oder `"ok"` /
      `"missing_credentials"` / `"network_error"` / `"invalid_ref"`.
    """

    ok: bool
    status: int
    code: str
    already_yanked: bool
    registry: str
    spec_ref: str
    detail: str | None = None
    spec_id: str | None = None
    version: str | None = None
    yank_status: str | None = None
    yank_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "code": self.code,
            "already_yanked": self.already_yanked,
            "registry": self.registry,
            "spec_ref": self.spec_ref,
            "detail": self.detail,
            "id": self.spec_id,
            "version": self.version,
            "yank_status": self.yank_status,
            "yank_reason": self.yank_reason,
            "raw": dict(self.raw),
        }


def run_yank(
    *,
    spec_ref: str,
    registry: str,
    reason: str | None = None,
    token: str | None = None,
    timeout_s: float = 30.0,
) -> YankResult:
    """Yankt ``spec_ref`` (Form ``@scope/name@version``) an ``registry``."""

    base_url = registry.rstrip("/")

    match = _REF_RE.match(spec_ref)
    if match is None:
        return YankResult(
            ok=False,
            status=0,
            code="invalid_ref",
            already_yanked=False,
            registry=base_url,
            spec_ref=spec_ref,
            detail="Expected `@scope/name@version`, e.g. @org/button@0.1.0.",
        )
    scope = match.group("scope")
    name = match.group("name")
    version = match.group("version")

    auth_token = token
    if auth_token is None:
        credential = _credentials.get(base_url)
        if credential is None:
            return YankResult(
                ok=False,
                status=0,
                code="missing_credentials",
                already_yanked=False,
                registry=base_url,
                spec_ref=spec_ref,
                detail=(
                    f"Not logged in for {base_url}. "
                    f"Run `speccify login --registry {base_url}` first."
                ),
            )
        auth_token = credential.token

    payload: dict[str, str] = {}
    if reason:
        payload["reason"] = reason

    try:
        response = httpx.post(
            f"{base_url}/api/v1/registry/specs/{scope}/{name}/{version}/yank",
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=httpx.Timeout(timeout_s, connect=5.0),
        )
    except httpx.HTTPError as exc:
        return YankResult(
            ok=False,
            status=0,
            code="network_error",
            already_yanked=False,
            registry=base_url,
            spec_ref=spec_ref,
            detail=str(exc),
        )

    try:
        body = response.json()
    except ValueError:
        body = {}

    if response.status_code == 200:
        return YankResult(
            ok=True,
            status=200,
            code="ok",
            already_yanked=bool(body.get("already_yanked")) if isinstance(body, dict) else False,
            registry=base_url,
            spec_ref=spec_ref,
            detail=None,
            spec_id=body.get("id") if isinstance(body, dict) else None,
            version=body.get("version") if isinstance(body, dict) else None,
            yank_status=body.get("yank_status") if isinstance(body, dict) else None,
            yank_reason=body.get("yank_reason") if isinstance(body, dict) else None,
            raw=body if isinstance(body, dict) else {},
        )

    code = (body.get("code") if isinstance(body, dict) else None) or (
        "unauthorized" if response.status_code == 401 else "error"
    )
    detail = (body.get("detail") if isinstance(body, dict) else None) or response.text or None
    return YankResult(
        ok=False,
        status=response.status_code,
        code=code,
        already_yanked=False,
        registry=base_url,
        spec_ref=spec_ref,
        detail=detail,
        raw=body if isinstance(body, dict) else {},
    )
