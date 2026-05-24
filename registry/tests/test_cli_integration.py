"""End-to-end tests for ``speccify login`` and ``speccify whoami`` against a live registry.

Lives under ``registry/tests/`` (not ``cli/tests/``) because the live
server fixture is provided by ``pytest-django`` and the registry test
suite is the one already bootstrapping Django.
"""

from __future__ import annotations

import threading
import time

import pytest
from django.contrib.auth import get_user_model
from speccify_cli import _credentials
from speccify_cli.__main__ import app
from speccify_registry.api.models import DeviceCode
from typer.testing import CliRunner

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def _isolated_config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SPECCIFY_CONFIG_HOME", str(tmp_path / "speccify"))
    # Silence the CLI's webbrowser.open() in headless test runs.
    import webbrowser

    monkeypatch.setattr(webbrowser, "open", lambda url: True)
    yield tmp_path


def _auto_approve_when_pending(base_url: str, username: str, deadline: float) -> None:
    """Background helper: as soon as a pending DeviceCode appears, approve it."""

    from django.test import Client

    user = get_user_model().objects.create_user(username=username, password="pw-12345678")
    client = Client()
    client.force_login(user)

    while time.monotonic() < deadline:
        dc = DeviceCode.objects.filter(status="pending").first()
        if dc is not None:
            client.post(
                "/auth/device",
                data={"user_code": dc.user_code, "action": "approve", "totp": ""},
            )
            return
        time.sleep(0.1)


def test_login_persists_token_and_whoami_returns_username(live_server) -> None:
    base_url = live_server.url
    deadline = time.monotonic() + 10
    approver = threading.Thread(
        target=_auto_approve_when_pending,
        args=(base_url, "marc", deadline),
        daemon=True,
    )
    approver.start()

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "login",
            "--registry",
            base_url,
            "--no-open-browser",
            "--max-wait-seconds",
            "10",
        ],
    )
    approver.join(timeout=2)

    assert result.exit_code == 0, result.output
    assert "Logged in" in result.output

    credential = _credentials.get(base_url)
    assert credential is not None
    assert credential.token.startswith("speccify_")

    whoami = runner.invoke(app, ["whoami", "--registry", base_url])
    assert whoami.exit_code == 0
    assert "username: marc" in whoami.output


def test_whoami_without_credentials_exits_1(live_server) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["whoami", "--registry", live_server.url])
    assert result.exit_code == 1
    assert "Not logged in" in result.output
