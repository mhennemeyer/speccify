"""End-to-end tests for the MCP `yank` tool against a live registry."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from speccify_cli import _credentials
from speccify_mcp.tools import run_yank
from speccify_registry.api.models import Scope, Spec, SpecVersion, YankStatus
from speccify_registry.api.tokens import mint_token

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
    return user, minted.cleartext


def _seed_published_version(owner) -> SpecVersion:
    scope, _ = Scope.objects.get_or_create(name="org", defaults={"owner": owner})
    spec, _ = Spec.objects.get_or_create(scope=scope, name="button")
    return SpecVersion.objects.create(
        spec=spec,
        version="0.1.0",
        yaml_bytes=b"id: '@org/button'\nversion: 0.1.0\n",
        sha256="a" * 64,
        uploader=owner,
    )


def test_yank_marks_version_yanked(live_server) -> None:
    owner, _ = _seed_user_and_credential(live_server.url)
    _seed_published_version(owner)

    result = run_yank(
        spec_ref="@org/button@0.1.0",
        registry=live_server.url,
        reason="security bug",
    ).to_dict()

    assert result["ok"] is True
    assert result["status"] == 200
    assert result["code"] == "ok"
    assert result["already_yanked"] is False
    assert result["yank_status"] == "yanked"
    assert result["yank_reason"] == "security bug"
    sv = SpecVersion.objects.get(spec__scope__name="org", spec__name="button")
    assert sv.yank_status == YankStatus.YANKED


def test_yank_idempotent_second_call(live_server) -> None:
    owner, _ = _seed_user_and_credential(live_server.url)
    _seed_published_version(owner)

    first = run_yank(spec_ref="@org/button@0.1.0", registry=live_server.url, reason="bad").to_dict()
    second = run_yank(spec_ref="@org/button@0.1.0", registry=live_server.url).to_dict()

    assert first["ok"] and second["ok"]
    assert first["already_yanked"] is False
    assert second["already_yanked"] is True
    assert second["yank_reason"] == "bad"


def test_yank_scope_forbidden(live_server) -> None:
    alice = get_user_model().objects.create_user(username="alice", password="pw-12345678")
    _seed_published_version(alice)
    _seed_user_and_credential(live_server.url, username="marc")

    result = run_yank(spec_ref="@org/button@0.1.0", registry=live_server.url).to_dict()

    assert result["ok"] is False
    assert result["code"] == "scope_forbidden"


def test_yank_version_not_found(live_server) -> None:
    _seed_user_and_credential(live_server.url)

    result = run_yank(spec_ref="@org/missing@9.9.9", registry=live_server.url).to_dict()

    assert result["ok"] is False
    assert result["status"] == 404
    assert result["code"] == "version_not_found"


def test_yank_stale_2fa(live_server) -> None:
    owner, _ = _seed_user_and_credential(live_server.url, fresh_2fa=False)
    _seed_published_version(owner)

    result = run_yank(spec_ref="@org/button@0.1.0", registry=live_server.url).to_dict()

    assert result["ok"] is False
    assert result["code"] == "stale_2fa"


def test_yank_missing_credentials_without_token(live_server) -> None:
    result = run_yank(spec_ref="@org/button@0.1.0", registry=live_server.url).to_dict()

    assert result["ok"] is False
    assert result["status"] == 0
    assert result["code"] == "missing_credentials"
    assert "speccify login" in (result["detail"] or "")


def test_yank_explicit_token_bypasses_credentials_file(live_server) -> None:
    """Passing `token=` should work without a credentials file present."""

    owner, token = _seed_user_and_credential(live_server.url)
    _seed_published_version(owner)
    creds_path = _credentials.credentials_path()
    if creds_path.exists():
        creds_path.unlink()

    result = run_yank(
        spec_ref="@org/button@0.1.0",
        registry=live_server.url,
        token=token,
    ).to_dict()

    assert result["ok"] is True
    assert result["already_yanked"] is False


def test_yank_invalid_ref_returns_structured_error() -> None:
    result = run_yank(spec_ref="not-a-ref", registry="http://localhost:1").to_dict()

    assert result["ok"] is False
    assert result["status"] == 0
    assert result["code"] == "invalid_ref"
