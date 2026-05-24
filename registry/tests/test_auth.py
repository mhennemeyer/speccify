"""Tests for signup/login/2FA-setup/tokens + Bearer authentication."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.oath import totp as totp_oath

from speccify_registry.api.models import ApiToken
from speccify_registry.api.tokens import mint_token

pytestmark = pytest.mark.django_db


def _make_user(username: str = "marc"):
    return get_user_model().objects.create_user(username=username, password="pw-12345678")


def test_signup_creates_user_and_logs_in() -> None:
    client = Client()
    response = client.post(
        "/auth/signup",
        data={"username": "marc", "password": "pw-12345678"},
    )
    assert response.status_code == 302
    assert get_user_model().objects.filter(username="marc").exists()
    # Auto-logged-in: tokens page is reachable (after redirect).
    tokens = client.get("/auth/tokens")
    assert tokens.status_code == 200


def test_login_with_bad_credentials_re_renders_form() -> None:
    _make_user()
    response = Client().post(
        "/auth/login", data={"username": "marc", "password": "wrong"}
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.content


def test_totp_setup_then_confirm() -> None:
    user = _make_user()
    client = Client()
    client.force_login(user)

    page = client.get("/auth/2fa-setup")
    assert page.status_code == 200
    device = TOTPDevice.objects.get(user=user, name="default")
    assert device.confirmed is False

    # Compute the current code from the device secret like an authenticator would.
    code = f"{totp_oath(device.bin_key, t0=device.t0, step=device.step, digits=device.digits, drift=0):0{device.digits}d}"
    response = client.post("/auth/2fa-setup", data={"token": code})
    assert response.status_code == 302
    device.refresh_from_db()
    assert device.confirmed is True


def test_totp_setup_rejects_bad_code() -> None:
    user = _make_user()
    client = Client()
    client.force_login(user)
    client.get("/auth/2fa-setup")
    response = client.post("/auth/2fa-setup", data={"token": "000000"})
    assert response.status_code == 200
    assert b"Invalid code" in response.content


def test_create_token_without_2fa_then_use_bearer_for_whoami() -> None:
    user = _make_user()
    client = Client()
    client.force_login(user)

    response = client.post("/auth/tokens", data={"label": "cli@laptop", "totp": ""})
    assert response.status_code == 200
    # Token cleartext is rendered once.
    assert b"speccify_" in response.content
    assert ApiToken.objects.filter(user=user).count() == 1

    # Use the bearer for the API whoami.
    token = ApiToken.objects.get(user=user)
    minted = mint_token(user=user, label="api-test")  # second token for direct call
    api = Client().get(
        "/api/v1/registry/whoami",
        HTTP_AUTHORIZATION=f"Bearer {minted.cleartext}",
    )
    assert api.status_code == 200
    assert api.json() == {"username": "marc", "scopes": []}
    # Original token still exists and isn't revoked.
    assert token.revoked_at is None


def test_whoami_rejects_invalid_bearer() -> None:
    response = Client().get(
        "/api/v1/registry/whoami",
        HTTP_AUTHORIZATION="Bearer speccify_not-a-real-token",
    )
    assert response.status_code == 401


def test_revoke_token() -> None:
    user = _make_user()
    minted = mint_token(user=user, label="cli@laptop")
    client = Client()
    client.force_login(user)

    response = client.post(f"/auth/tokens/{minted.token.id}/revoke")
    assert response.status_code == 302
    minted.token.refresh_from_db()
    assert minted.token.revoked_at is not None

    # Revoked token can no longer authenticate.
    api = Client().get(
        "/api/v1/registry/whoami",
        HTTP_AUTHORIZATION=f"Bearer {minted.cleartext}",
    )
    assert api.status_code == 401


def test_create_token_with_2fa_rejects_bad_code() -> None:
    user = _make_user()
    TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    client = Client()
    client.force_login(user)

    response = client.post("/auth/tokens", data={"label": "x", "totp": "000000"})
    assert response.status_code == 200
    assert b"Invalid 2FA code" in response.content
    assert ApiToken.objects.filter(user=user).count() == 0


def test_create_token_with_2fa_accepts_correct_code() -> None:
    user = _make_user()
    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    client = Client()
    client.force_login(user)

    code = f"{totp_oath(device.bin_key, t0=device.t0, step=device.step, digits=device.digits, drift=0):0{device.digits}d}"
    response = client.post("/auth/tokens", data={"label": "x", "totp": code})
    assert response.status_code == 200
    tok = ApiToken.objects.get(user=user)
    assert tok.requires_2fa is True
    assert tok.last_2fa_verified_at is not None
    assert (timezone.now() - tok.last_2fa_verified_at).total_seconds() < 60
