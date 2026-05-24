"""End-to-end tests for ``speccify publish`` against a live registry.

Lives under ``registry/tests/`` for the same reason as
``test_cli_integration.py``: only the registry suite bootstraps Django
and provides the ``live_server`` fixture from pytest-django.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from speccify_cli import _credentials
from speccify_cli.__main__ import app
from speccify_registry.api.models import Scope, ScopeReservation, SpecVersion
from speccify_registry.api.tokens import mint_token
from typer.testing import CliRunner

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
        label="cli",
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


def _write_spec(tmp_path, content: bytes = _VALID_SPEC):
    path = tmp_path / "button.speccify.yaml"
    path.write_bytes(content)
    return path


def test_publish_uploads_spec_and_persists_version(live_server, tmp_path) -> None:
    _seed_user_and_credential(live_server.url)
    spec_path = _write_spec(tmp_path)

    result = CliRunner().invoke(
        app,
        ["publish", str(spec_path), "--registry", live_server.url],
    )

    assert result.exit_code == 0, result.output
    assert "Published" in result.output
    assert "@org/button@0.1.0" in result.output

    version = SpecVersion.objects.get(spec__scope__name="org", spec__name="button")
    assert version.version == "0.1.0"
    assert bytes(version.yaml_bytes) == _VALID_SPEC


def test_publish_idempotent_second_call(live_server, tmp_path) -> None:
    _seed_user_and_credential(live_server.url)
    spec_path = _write_spec(tmp_path)
    runner = CliRunner()

    first = runner.invoke(app, ["publish", str(spec_path), "--registry", live_server.url])
    assert first.exit_code == 0
    second = runner.invoke(app, ["publish", str(spec_path), "--registry", live_server.url])
    assert second.exit_code == 0
    assert "idempotent" in second.output.lower()
    assert SpecVersion.objects.count() == 1


def test_publish_version_conflict_exits_2(live_server, tmp_path) -> None:
    _seed_user_and_credential(live_server.url)
    spec_path = _write_spec(tmp_path)
    runner = CliRunner()

    first = runner.invoke(app, ["publish", str(spec_path), "--registry", live_server.url])
    assert first.exit_code == 0

    drifted = _VALID_SPEC.replace(b"A clickable thing.", b"Drifted summary.")
    spec_path.write_bytes(drifted)
    result = runner.invoke(app, ["publish", str(spec_path), "--registry", live_server.url])

    assert result.exit_code == 2, result.output
    assert "Version conflict" in result.output


def test_publish_scope_forbidden_exits_2(live_server, tmp_path) -> None:
    # User "marc" tries to publish into a scope owned by someone else.
    other = get_user_model().objects.create_user(username="alice", password="pw-12345678")
    Scope.objects.create(name="org", owner=other)
    _seed_user_and_credential(live_server.url)
    spec_path = _write_spec(tmp_path)

    result = CliRunner().invoke(app, ["publish", str(spec_path), "--registry", live_server.url])

    assert result.exit_code == 2
    assert "Scope error" in result.output


def test_publish_stale_2fa_exits_1(live_server, tmp_path) -> None:
    _seed_user_and_credential(live_server.url, fresh_2fa=False)
    spec_path = _write_spec(tmp_path)

    result = CliRunner().invoke(app, ["publish", str(spec_path), "--registry", live_server.url])

    assert result.exit_code == 1
    assert "2FA" in result.output


def test_publish_without_credentials_exits_1(live_server, tmp_path) -> None:
    spec_path = _write_spec(tmp_path)

    result = CliRunner().invoke(app, ["publish", str(spec_path), "--registry", live_server.url])

    assert result.exit_code == 1
    assert "Not logged in" in result.output


def test_publish_scope_reserved_exits_2(live_server, tmp_path) -> None:
    ScopeReservation.objects.create(name="org")
    _seed_user_and_credential(live_server.url)
    spec_path = _write_spec(tmp_path)

    result = CliRunner().invoke(app, ["publish", str(spec_path), "--registry", live_server.url])

    assert result.exit_code == 2
    assert "Scope error" in result.output
