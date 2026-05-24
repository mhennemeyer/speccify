"""`speccify whoami` — print the username + scopes associated with the stored token."""

from __future__ import annotations

from typing import Annotated

import httpx
import typer

from .. import _credentials


def whoami_command(
    registry: Annotated[
        str,
        typer.Option(
            "--registry",
            "-r",
            help="Registry base URL (e.g. http://localhost:8001).",
        ),
    ],
) -> None:
    base_url = registry.rstrip("/")
    credential = _credentials.get(base_url)
    if credential is None:
        typer.echo(
            f"Not logged in for {base_url}. Run `speccify login --registry {base_url}` first.",
            err=True,
        )
        raise typer.Exit(code=1)

    response = httpx.get(
        f"{base_url}/api/v1/registry/whoami",
        headers={"Authorization": f"Bearer {credential.token}"},
        timeout=httpx.Timeout(10.0, connect=5.0),
    )
    if response.status_code == 401:
        typer.echo("Token rejected — run `speccify login` again.", err=True)
        raise typer.Exit(code=1)
    if response.status_code != 200:
        typer.echo(
            f"Unexpected response: {response.status_code} {response.text}",
            err=True,
        )
        raise typer.Exit(code=1)

    body = response.json()
    scopes = ", ".join(body.get("scopes") or []) or "—"
    typer.echo(f"username: {body['username']}")
    typer.echo(f"scopes:   {scopes}")
