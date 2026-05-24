"""`speccify publish` — upload a spec YAML to a Speccify registry.

Thin adapter over the Phase-2 registry ``POST /api/v1/registry/specs/publish``
endpoint. Reads the YAML bytes verbatim (no re-serialisation) so that the
server-side ``sha256`` matches what the CLI- and MCP-emitted lockfiles
record.

Exit codes:
  0  — Created (201) or re-publish of identical bytes (200, idempotent).
  1  — Network/IO error, missing credentials, or stale 2FA.
  2  — Scope forbidden or version conflict (bytes drift under same version).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import httpx
import typer

from .. import _credentials


def publish_command(
    spec: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to the spec YAML file to publish.",
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
) -> None:
    """Publish a spec YAML to the configured Speccify registry."""

    base_url = registry.rstrip("/")
    credential = _credentials.get(base_url)
    if credential is None:
        typer.echo(
            f"Not logged in for {base_url}. Run `speccify login --registry {base_url}` first.",
            err=True,
        )
        raise typer.Exit(code=1)

    yaml_bytes = spec.read_bytes()
    response = httpx.post(
        f"{base_url}/api/v1/registry/specs/publish",
        files={"yaml": (spec.name, yaml_bytes, "application/x-yaml")},
        headers={"Authorization": f"Bearer {credential.token}"},
        timeout=httpx.Timeout(30.0, connect=5.0),
    )

    if response.status_code in (200, 201):
        body = response.json()
        verb = "Published" if response.status_code == 201 else "Already published (idempotent)"
        typer.echo(f"✓ {verb}: {body['id']}@{body['version']} (sha256={body['sha256'][:12]}…)")
        return

    # Map server-side error codes to user-friendly messages.
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
            "Token's 2FA verification is stale. Re-mint the token in the web UI to publish.",
            err=True,
        )
        raise typer.Exit(code=1)
    if code in ("scope_forbidden", "scope_reserved"):
        typer.echo(f"Scope error: {detail}", err=True)
        raise typer.Exit(code=2)
    if code == "version_conflict":
        typer.echo(f"Version conflict: {detail}", err=True)
        raise typer.Exit(code=2)

    typer.echo(f"Publish failed ({response.status_code}, {code}): {detail}", err=True)
    raise typer.Exit(code=1)
