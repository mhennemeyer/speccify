"""`speccify login` — OAuth-style device-code flow against a registry.

UX mirrors ``gh auth login``: the CLI asks the registry for a device code,
prints a user-friendly code, opens the browser at the verification URL,
and then polls until the user approves the request in the web UI. On
approval the registry returns a freshly-minted API token which is
persisted in ``~/.config/speccify/credentials.toml`` with ``0600``.
"""

from __future__ import annotations

import time
import webbrowser
from typing import Annotated

import httpx
import typer

from .. import _credentials

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _poll_once(client: httpx.Client, base_url: str, device_code: str) -> dict:
    response = client.post(
        f"{base_url}/api/v1/registry/auth/device-code/poll",
        json={"device_code": device_code},
        timeout=DEFAULT_TIMEOUT,
    )
    if response.status_code != 200:
        raise httpx.HTTPStatusError(
            f"poll failed: {response.status_code} {response.text}",
            request=response.request,
            response=response,
        )
    return response.json()


def login_command(
    registry: Annotated[
        str,
        typer.Option(
            "--registry",
            "-r",
            help="Registry base URL (e.g. http://localhost:8001).",
        ),
    ],
    open_browser: Annotated[
        bool,
        typer.Option(
            "--open-browser/--no-open-browser",
            help="Whether to open the verification URL in a browser.",
        ),
    ] = True,
    max_wait_seconds: Annotated[
        int,
        typer.Option(
            "--max-wait-seconds",
            help="Abort polling after this many seconds.",
        ),
    ] = 600,
) -> None:
    """Authenticate the CLI against a Speccify registry via device-code flow."""

    base_url = registry.rstrip("/")
    with httpx.Client() as client:
        start = client.post(
            f"{base_url}/api/v1/registry/auth/device-code",
            timeout=DEFAULT_TIMEOUT,
        )
        if start.status_code not in (200, 201):
            typer.echo(
                f"Failed to start device-code flow: {start.status_code} {start.text}",
                err=True,
            )
            raise typer.Exit(code=1)
        payload = start.json()
        user_code = payload["user_code"]
        device_code = payload["device_code"]
        verification_url = payload["verification_url"]
        interval = max(1, int(payload.get("interval", 5)))

        typer.echo("Open the following URL in your browser to approve this CLI:")
        typer.echo(f"  {verification_url}?user_code={user_code}")
        typer.echo(f"and enter the code: {user_code}")

        if open_browser:
            try:
                webbrowser.open(f"{verification_url}?user_code={user_code}")
            except webbrowser.Error:  # pragma: no cover - environment-dependent
                pass

        deadline = time.monotonic() + max_wait_seconds
        while time.monotonic() < deadline:
            result = _poll_once(client, base_url, device_code)
            if "token" in result:
                credential = _credentials.Credential(
                    registry=_credentials.normalize_registry_url(base_url),
                    token=result["token"],
                )
                path = _credentials.save(credential)
                typer.echo(f"✓ Logged in. Token stored in {path}.")
                return
            status_value = result.get("status")
            if status_value in ("expired", "denied"):
                typer.echo(f"Login {status_value}.", err=True)
                raise typer.Exit(code=1)
            time.sleep(interval)

        typer.echo("Login timed out.", err=True)
        raise typer.Exit(code=1)
