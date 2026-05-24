"""Tests for the yank REST endpoint (Phase 2, Stage 5)."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from speccify_registry.api.models import Scope, Spec, SpecVersion, YankStatus
from speccify_registry.api.tokens import mint_token

pytestmark = pytest.mark.django_db


def _make_user_with_token(
    username: str = "marc",
    *,
    fresh_2fa: bool = True,
) -> tuple:
    user = get_user_model().objects.create_user(username=username, password="pw-12345678")
    last = timezone.now() if fresh_2fa else timezone.now() - timedelta(hours=1)
    minted = mint_token(
        user=user,
        label="cli",
        requires_2fa=True,
        last_2fa_verified_at=last,
    )
    return user, minted


def _seed_version(owner, *, scope_name: str = "org", name: str = "button") -> SpecVersion:
    scope, _ = Scope.objects.get_or_create(name=scope_name, defaults={"owner": owner})
    spec, _ = Spec.objects.get_or_create(scope=scope, name=name)
    return SpecVersion.objects.create(
        spec=spec,
        version="0.1.0",
        yaml_bytes=b"id: '@org/button'\nversion: 0.1.0\n",
        sha256="a" * 64,
        uploader=owner,
    )


def _yank(client: Client, token: str, scope: str, name: str, version: str, reason: str = ""):
    body = {"reason": reason} if reason else {}
    return client.post(
        f"/api/v1/registry/specs/{scope}/{name}/{version}/yank",
        data=json.dumps(body),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


# --- happy path -------------------------------------------------------


def test_yank_marks_version_yanked() -> None:
    owner, minted = _make_user_with_token()
    sv = _seed_version(owner)

    response = _yank(Client(), minted.cleartext, "org", "button", "0.1.0", reason="security bug")
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["yank_status"] == "yanked"
    assert body["yank_reason"] == "security bug"
    assert body["already_yanked"] is False

    sv.refresh_from_db()
    assert sv.yank_status == YankStatus.YANKED
    assert sv.yank_reason == "security bug"
    # bytes + sha256 must remain untouched.
    assert sv.sha256 == "a" * 64


def test_yank_is_idempotent_and_preserves_original_reason() -> None:
    owner, minted = _make_user_with_token()
    _seed_version(owner)
    client = Client()

    first = _yank(client, minted.cleartext, "org", "button", "0.1.0", reason="original")
    assert first.status_code == 200
    assert first.json()["already_yanked"] is False

    # Re-yank without a new reason must keep the original one.
    second = _yank(client, minted.cleartext, "org", "button", "0.1.0")
    assert second.status_code == 200
    body = second.json()
    assert body["already_yanked"] is True
    assert body["yank_reason"] == "original"


def test_yank_updates_reason_on_re_yank_when_supplied() -> None:
    owner, minted = _make_user_with_token()
    _seed_version(owner)
    client = Client()

    _yank(client, minted.cleartext, "org", "button", "0.1.0", reason="old")
    second = _yank(client, minted.cleartext, "org", "button", "0.1.0", reason="updated")
    assert second.status_code == 200
    assert second.json()["yank_reason"] == "updated"
    assert second.json()["already_yanked"] is True


def test_yank_versions_endpoint_reflects_status() -> None:
    owner, minted = _make_user_with_token()
    _seed_version(owner)
    client = Client()

    _yank(client, minted.cleartext, "org", "button", "0.1.0", reason="bad")
    listing = client.get("/api/v1/registry/specs/org/button").json()
    versions = {v["version"]: v for v in listing["versions"]}
    assert versions["0.1.0"]["yank_status"] == "yanked"
    assert versions["0.1.0"]["yank_reason"] == "bad"


# --- error cases ------------------------------------------------------


def test_yank_requires_authentication() -> None:
    owner, _ = _make_user_with_token()
    _seed_version(owner)
    response = Client().post(
        "/api/v1/registry/specs/org/button/0.1.0/yank",
        data="{}",
        content_type="application/json",
    )
    assert response.status_code == 401


def test_yank_rejects_stale_2fa() -> None:
    owner, minted = _make_user_with_token(fresh_2fa=False)
    _seed_version(owner)
    response = _yank(Client(), minted.cleartext, "org", "button", "0.1.0")
    assert response.status_code == 403
    assert response.json()["code"] == "stale_2fa"


def test_yank_rejects_non_owner() -> None:
    owner, _ = _make_user_with_token(username="alice")
    _seed_version(owner)
    # A second user with a token that does NOT own @org.
    _, minted_b = _make_user_with_token(username="bob")
    response = _yank(Client(), minted_b.cleartext, "org", "button", "0.1.0")
    assert response.status_code == 403
    assert response.json()["code"] == "scope_forbidden"


def test_yank_404_for_unknown_version() -> None:
    owner, minted = _make_user_with_token()
    _seed_version(owner)
    response = _yank(Client(), minted.cleartext, "org", "button", "9.9.9")
    assert response.status_code == 404
    assert response.json()["code"] == "version_not_found"


def test_yank_404_for_unknown_spec() -> None:
    _, minted = _make_user_with_token()
    response = _yank(Client(), minted.cleartext, "org", "missing", "0.1.0")
    assert response.status_code == 404
    assert response.json()["code"] == "version_not_found"


def test_yank_does_not_modify_bytes_or_hash() -> None:
    owner, minted = _make_user_with_token()
    sv = _seed_version(owner)
    original_bytes = bytes(sv.yaml_bytes)
    original_sha = sv.sha256

    _yank(Client(), minted.cleartext, "org", "button", "0.1.0", reason="bad")
    sv.refresh_from_db()
    assert bytes(sv.yaml_bytes) == original_bytes
    assert sv.sha256 == original_sha
