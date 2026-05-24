"""End-to-end tests for ``speccify yank`` against a live registry."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from speccify_cli import _credentials
from speccify_cli.__main__ import app
from speccify_registry.api.models import Scope, Spec, SpecVersion, YankStatus
from speccify_registry.api.tokens import mint_token
from typer.testing import CliRunner

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def _isolated_config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SPECCIFY_CONFIG_HOME", str(tmp_path / "speccify"))
    yield tmp_path


def _seed_user_and_credential(base_url: str, *, username: str = "marc", fresh_2fa: bool = True):
    user = get_user_model().objects.create_user(username=username, password="pw-12345678")
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
    return user


def _seed_published_version(owner, *, scope_name: str = "org", name: str = "button") -> SpecVersion:
    scope, _ = Scope.objects.get_or_create(name=scope_name, defaults={"owner": owner})
    spec, _ = Spec.objects.get_or_create(scope=scope, name=name)
    return SpecVersion.objects.create(
        spec=spec,
        version="0.1.0",
        yaml_bytes=b"id: '@org/button'\nversion: 0.1.0\n",
        sha256="a" * 64,
        uploader=owner,
    )


def test_yank_marks_version_yanked(live_server) -> None:
    owner = _seed_user_and_credential(live_server.url)
    _seed_published_version(owner)

    result = CliRunner().invoke(
        app,
        ["yank", "@org/button@0.1.0", "--registry", live_server.url, "--reason", "security bug"],
    )
    assert result.exit_code == 0, result.output
    assert "Yanked" in result.output
    assert "@org/button@0.1.0" in result.output

    sv = SpecVersion.objects.get(spec__scope__name="org", spec__name="button")
    assert sv.yank_status == YankStatus.YANKED
    assert sv.yank_reason == "security bug"


def test_yank_idempotent_second_call(live_server) -> None:
    owner = _seed_user_and_credential(live_server.url)
    _seed_published_version(owner)
    runner = CliRunner()

    first = runner.invoke(
        app, ["yank", "@org/button@0.1.0", "--registry", live_server.url, "--reason", "bad"]
    )
    assert first.exit_code == 0
    second = runner.invoke(app, ["yank", "@org/button@0.1.0", "--registry", live_server.url])
    assert second.exit_code == 0
    assert "Already yanked" in second.output


def test_yank_scope_forbidden_exits_2(live_server) -> None:
    # Marc has credentials, but @org is owned by alice.
    alice = get_user_model().objects.create_user(username="alice", password="pw-12345678")
    _seed_published_version(alice)
    _seed_user_and_credential(live_server.url, username="marc")

    result = CliRunner().invoke(app, ["yank", "@org/button@0.1.0", "--registry", live_server.url])
    assert result.exit_code == 2, result.output
    assert "Scope error" in result.output


def test_yank_version_not_found_exits_2(live_server) -> None:
    _seed_user_and_credential(live_server.url)

    result = CliRunner().invoke(app, ["yank", "@org/missing@9.9.9", "--registry", live_server.url])
    assert result.exit_code == 2
    assert "Version not found" in result.output


def test_yank_stale_2fa_exits_1(live_server) -> None:
    owner = _seed_user_and_credential(live_server.url, fresh_2fa=False)
    _seed_published_version(owner)

    result = CliRunner().invoke(app, ["yank", "@org/button@0.1.0", "--registry", live_server.url])
    assert result.exit_code == 1
    assert "2FA" in result.output


def test_yank_without_credentials_exits_1(live_server) -> None:
    result = CliRunner().invoke(app, ["yank", "@org/button@0.1.0", "--registry", live_server.url])
    assert result.exit_code == 1
    assert "Not logged in" in result.output


def test_yank_invalid_ref_exits_2(live_server) -> None:
    _seed_user_and_credential(live_server.url)
    result = CliRunner().invoke(app, ["yank", "not-a-ref", "--registry", live_server.url])
    assert result.exit_code == 2
    assert "Invalid spec reference" in result.output
