"""End-to-end tests for the MCP `publish` tool against a live registry.

Lives under ``registry/tests/`` because only the registry suite
bootstraps Django and exposes the ``live_server`` fixture (same
reason as ``test_cli_publish.py`` / ``test_cli_integration.py``).
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from speccify_cli import _credentials
from speccify_mcp.tools import run_publish
from speccify_registry.api.models import Scope, ScopeReservation, SpecVersion
from speccify_registry.api.tokens import mint_token

pytestmark = pytest.mark.django_db(transaction=True)


_VALID_SPEC = b"""\
id: "@org/button"
version: 0.1.0
kind: ui-component
title: Button
summary: A clickable thing.
authors: [marc@speccify.io]
license: MIT
inputs:
  - name: label
    type: string
    constraints: ["minLength=1"]
events:
  - name: pressed
acceptance:
  - given: button rendered
    when: user clicks
    then: pressed event fires once
"""


@pytest.fixture(autouse=True)
def _isolated_config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SPECCIFY_CONFIG_HOME", str(tmp_path / "speccify"))
    yield tmp_path


def _seed_user_and_credential(base_url: str, *, fresh_2fa: bool = True) -> str:
    user = get_user_model().objects.create_user(username="marc", password="pw-12345678")
    last = timezone.now() if fresh_2fa else timezone.now() - timedelta(hours=1)
    minted = mint_token(
        user=user,
        label="mcp",
        requires_2fa=True,
        last_2fa_verified_at=last,
    )
    _credentials.save(
        _credentials.Credential(
            registry=_credentials.normalize_registry_url(base_url),
            token=minted.cleartext,
        )
    )
    return minted.cleartext


def _write_spec(tmp_path: Path, content: bytes = _VALID_SPEC) -> Path:
    path = tmp_path / "button.speccify.yaml"
    path.write_bytes(content)
    return path


def test_publish_creates_version(live_server, tmp_path) -> None:
    _seed_user_and_credential(live_server.url)
    spec_path = _write_spec(tmp_path)

    result = run_publish(spec_path=spec_path, registry=live_server.url).to_dict()

    assert result["ok"] is True
    assert result["status"] == 201
    assert result["code"] == "ok"
    assert result["created"] is True
    assert result["id"] == "@org/button"
    assert result["version"] == "0.1.0"
    assert result["sha256"]
    assert SpecVersion.objects.filter(version="0.1.0").exists()


def test_publish_idempotent_second_call(live_server, tmp_path) -> None:
    _seed_user_and_credential(live_server.url)
    spec_path = _write_spec(tmp_path)

    first = run_publish(spec_path=spec_path, registry=live_server.url).to_dict()
    second = run_publish(spec_path=spec_path, registry=live_server.url).to_dict()

    assert first["ok"] and second["ok"]
    assert first["created"] is True
    assert second["created"] is False
    assert second["status"] == 200
    assert SpecVersion.objects.count() == 1


def test_publish_version_conflict_returns_structured_error(live_server, tmp_path) -> None:
    _seed_user_and_credential(live_server.url)
    spec_path = _write_spec(tmp_path)
    assert run_publish(spec_path=spec_path, registry=live_server.url).ok

    drifted = _VALID_SPEC.replace(b"A clickable thing.", b"Drifted summary.")
    spec_path.write_bytes(drifted)
    result = run_publish(spec_path=spec_path, registry=live_server.url).to_dict()

    assert result["ok"] is False
    assert result["status"] == 409
    assert result["code"] == "version_conflict"
    assert result["detail"]


def test_publish_scope_forbidden(live_server, tmp_path) -> None:
    other = get_user_model().objects.create_user(username="alice", password="pw-12345678")
    Scope.objects.create(name="org", owner=other)
    _seed_user_and_credential(live_server.url)
    spec_path = _write_spec(tmp_path)

    result = run_publish(spec_path=spec_path, registry=live_server.url).to_dict()

    assert result["ok"] is False
    assert result["code"] == "scope_forbidden"


def test_publish_scope_reserved(live_server, tmp_path) -> None:
    ScopeReservation.objects.create(name="org")
    _seed_user_and_credential(live_server.url)
    spec_path = _write_spec(tmp_path)

    result = run_publish(spec_path=spec_path, registry=live_server.url).to_dict()

    assert result["ok"] is False
    assert result["code"] == "scope_reserved"


def test_publish_stale_2fa(live_server, tmp_path) -> None:
    _seed_user_and_credential(live_server.url, fresh_2fa=False)
    spec_path = _write_spec(tmp_path)

    result = run_publish(spec_path=spec_path, registry=live_server.url).to_dict()

    assert result["ok"] is False
    assert result["code"] == "stale_2fa"


def test_publish_missing_credentials_without_token(live_server, tmp_path) -> None:
    spec_path = _write_spec(tmp_path)

    result = run_publish(spec_path=spec_path, registry=live_server.url).to_dict()

    assert result["ok"] is False
    assert result["status"] == 0
    assert result["code"] == "missing_credentials"
    assert "speccify login" in (result["detail"] or "")


def test_publish_explicit_token_bypasses_credentials_file(live_server, tmp_path) -> None:
    """Passing `token=` should work without any credentials file present."""
    token = _seed_user_and_credential(live_server.url)
    # Wipe the credentials file to prove the explicit token is sufficient.
    creds_path = _credentials.credentials_path()
    if creds_path.exists():
        creds_path.unlink()
    spec_path = _write_spec(tmp_path)

    result = run_publish(spec_path=spec_path, registry=live_server.url, token=token).to_dict()

    assert result["ok"] is True
    assert result["created"] is True


def test_publish_missing_spec_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        run_publish(spec_path=tmp_path / "nope.yaml", registry="http://localhost:1")
