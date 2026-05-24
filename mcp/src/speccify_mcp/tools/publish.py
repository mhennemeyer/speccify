"""`publish`-Tool: lädt eine YAML-Spec in eine Speccify-Registry.

Dünner HTTP-Adapter über ``POST /api/v1/registry/specs/publish`` —
spiegelt 1:1 das CLI-Verhalten in
``cli/src/speccify_cli/commands/publish.py``, gibt jedoch — statt
Prozess-Exit-Codes — ein strukturiertes Dict zurück, damit der MCP-
Client (Coding-Agent) programmatisch reagieren kann.

Bytes werden verbatim gelesen (kein YAML-Round-Trip), damit der
``sha256``, den der Server berechnet, identisch ist mit dem, den
Lockfile/CLI/MCP-Render-Cache für dieselbe Datei berechnen würden.

Auth-Token wird aus der gleichen Credentials-Datei gelesen wie für
``speccify login`` (``~/.config/speccify/credentials.toml``); MCP-
Server und CLI teilen sich also den Login-State.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from speccify_cli import _credentials


@dataclass(frozen=True)
class PublishResult:
    """Strukturierter Output des `publish`-Tools.

    - ``ok``: True bei HTTP 200/201.
    - ``created``: True nur bei HTTP 201 (neu); False bei idempotentem
      Re-Publish (HTTP 200) oder Fehlern.
    - ``code``: Server-seitiger Error-Code (`scope_forbidden`,
      `scope_reserved`, `version_conflict`, `stale_2fa`, ...) oder
      `"ok"` / `"missing_credentials"` / `"network_error"`.
    - ``id`` / ``version`` / ``sha256``: bei Erfolg gesetzt.
    """

    ok: bool
    status: int
    code: str
    created: bool
    registry: str
    spec_path: str
    detail: str | None = None
    spec_id: str | None = None
    version: str | None = None
    sha256: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "code": self.code,
            "created": self.created,
            "registry": self.registry,
            "spec_path": self.spec_path,
            "detail": self.detail,
            "id": self.spec_id,
            "version": self.version,
            "sha256": self.sha256,
            "raw": dict(self.raw),
        }


def run_publish(
    *,
    spec_path: Path,
    registry: str,
    token: str | None = None,
    timeout_s: float = 30.0,
) -> PublishResult:
    """Publiziert ``spec_path`` an ``registry``.

    - ``token``: optionaler Override; wenn ``None``, wird das in der
      Credentials-Datei hinterlegte Token für diese Registry verwendet.
    - Wirft ``FileNotFoundError`` bei fehlender Spec-Datei (analog zu
      anderen Tools — Adapter lässt das durchschlagen, damit MCP
      ``isError: true`` mit klarer Diagnose liefert).
    - Netzwerk-/Transport-Fehler werden als ``PublishResult`` mit
      ``ok=False`` und ``code="network_error"`` zurückgegeben, damit
      Agents sie strukturiert behandeln können.
    """
    if not spec_path.is_file():
        raise FileNotFoundError(f"Spec-Datei nicht gefunden: {spec_path}")

    base_url = registry.rstrip("/")
    auth_token = token
    if auth_token is None:
        credential = _credentials.get(base_url)
        if credential is None:
            return PublishResult(
                ok=False,
                status=0,
                code="missing_credentials",
                created=False,
                registry=base_url,
                spec_path=str(spec_path),
                detail=(
                    f"Not logged in for {base_url}. "
                    f"Run `speccify login --registry {base_url}` first."
                ),
            )
        auth_token = credential.token

    yaml_bytes = spec_path.read_bytes()
    try:
        response = httpx.post(
            f"{base_url}/api/v1/registry/specs/publish",
            files={"yaml": (spec_path.name, yaml_bytes, "application/x-yaml")},
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=httpx.Timeout(timeout_s, connect=5.0),
        )
    except httpx.HTTPError as exc:
        return PublishResult(
            ok=False,
            status=0,
            code="network_error",
            created=False,
            registry=base_url,
            spec_path=str(spec_path),
            detail=str(exc),
        )

    try:
        body = response.json()
    except ValueError:
        body = {}

    if response.status_code in (200, 201):
        return PublishResult(
            ok=True,
            status=response.status_code,
            code="ok",
            created=response.status_code == 201,
            registry=base_url,
            spec_path=str(spec_path),
            detail=None,
            spec_id=body.get("id"),
            version=body.get("version"),
            sha256=body.get("sha256"),
            raw=body if isinstance(body, dict) else {},
        )

    code = (body.get("code") if isinstance(body, dict) else None) or (
        "unauthorized" if response.status_code == 401 else "error"
    )
    detail = (body.get("detail") if isinstance(body, dict) else None) or response.text or None
    return PublishResult(
        ok=False,
        status=response.status_code,
        code=code,
        created=False,
        registry=base_url,
        spec_path=str(spec_path),
        detail=detail,
        raw=body if isinstance(body, dict) else {},
    )
