"""`speccify yank` — mark a published spec version as yanked.

Thin adapter over the Phase-2 registry
``POST /api/v1/registry/specs/<scope>/<name>/<version>/yank`` endpoint.
Yanking does NOT delete bytes or change the sha256 — it only flips the
``yank_status`` so `speccify verify` can warn downstream users.

Exit codes:
  0  — Yanked (or re-yank of an already-yanked version, idempotent).
  1  — Network/IO error, missing credentials, or stale 2FA.
  2  — Scope forbidden or version not found.
"""

from __future__ import annotations

import re
from typing import Annotated

import httpx
import typer

from .. import _credentials

# ``@scope/name@version`` reference, e.g. ``@org/button@0.1.0``.
_REF_RE = re.compile(
    r"^@(?P<scope>[a-z0-9][a-z0-9-]*)/(?P<name>[a-z0-9][a-z0-9-]*)@"
    r"(?P<version>(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*))$"
)


def yank_command(
    spec_ref: Annotated[
        str,
        typer.Argument(
            help="Spec reference in the form `@scope/name@version` (e.g. @org/button@0.1.0).",
        ),
    ],
    registry: Annotated[
        str,
        typer.Option(
            "--registry",
            "-r",
            help="Registry base URL (e.g. http://localhost:8001).",
        ),
    ],
    reason: Annotated[
        str,
        typer.Option(
            "--reason",
            help="Optional explanation; preserved on re-yank when omitted.",
        ),
    ] = "",
) -> None:
    """Yank a published version of a spec."""

    match = _REF_RE.match(spec_ref)
    if match is None:
        typer.echo(
            "Invalid spec reference. Expected `@scope/name@version`, e.g. @org/button@0.1.0.",
            err=True,
        )
        raise typer.Exit(code=2)
    scope = match.group("scope")
    name = match.group("name")
    version = match.group("version")

    base_url = registry.rstrip("/")
    credential = _credentials.get(base_url)
    if credential is None:
        typer.echo(
            f"Not logged in for {base_url}. Run `speccify login --registry {base_url}` first.",
            err=True,
        )
        raise typer.Exit(code=1)

    payload: dict[str, str] = {}
    if reason:
        payload["reason"] = reason

    try:
        response = httpx.post(
            f"{base_url}/api/v1/registry/specs/{scope}/{name}/{version}/yank",
            json=payload,
            headers={"Authorization": f"Bearer {credential.token}"},
            timeout=httpx.Timeout(30.0, connect=5.0),
        )
    except httpx.HTTPError as exc:
        typer.echo(f"Network error contacting {base_url}: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if response.status_code == 200:
        body = response.json()
        verb = "Already yanked" if body.get("already_yanked") else "Yanked"
        reason_text = body.get("yank_reason")
        suffix = f" — reason: {reason_text}" if reason_text else ""
        typer.echo(f"✓ {verb}: @{scope}/{name}@{version}{suffix}")
        return

    try:
        body = response.json()
    except ValueError:
        body = {}
    code = body.get("code") or "error"
    detail = body.get("detail") or response.text

    if response.status_code == 401:
        typer.echo("Token rejected — run `speccify login` again.", err=True)
        raise typer.Exit(code=1)
    if code == "stale_2fa":
        typer.echo(
            "Token's 2FA verification is stale. Re-mint the token in the web UI to yank.",
            err=True,
        )
        raise typer.Exit(code=1)
    if code == "scope_forbidden":
        typer.echo(f"Scope error: {detail}", err=True)
        raise typer.Exit(code=2)
    if code == "version_not_found":
        typer.echo(f"Version not found: {detail}", err=True)
        raise typer.Exit(code=2)

    typer.echo(f"Yank failed ({response.status_code}, {code}): {detail}", err=True)
    raise typer.Exit(code=1)
