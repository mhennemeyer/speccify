"""Tests for the device-code REST flow + web approval."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from speccify_registry.api import device_codes
from speccify_registry.api.models import DeviceCode, DeviceCodeStatus

pytestmark = pytest.mark.django_db


def test_start_endpoint_issues_codes() -> None:
    response = Client().post("/api/v1/registry/auth/device-code")
    assert response.status_code == 201
    body = response.json()
    assert body["user_code"]
    assert body["device_code"]
    assert body["verification_url"].endswith("/auth/device")
    assert body["expires_in"] > 0
    assert body["interval"] >= 1


def test_poll_pending_then_approved_then_consumed() -> None:
    User = get_user_model()
    user = User.objects.create_user(username="marc", password="pw-12345678")
    client = Client()
    client.force_login(user)

    start = client.post("/api/v1/registry/auth/device-code").json()
    device_code = start["device_code"]
    user_code = start["user_code"]

    # Pending while nobody approved.
    pending = Client().post(
        "/api/v1/registry/auth/device-code/poll",
        data={"device_code": device_code},
        content_type="application/json",
    )
    assert pending.status_code == 200
    assert pending.json() == {"status": "pending"}

    # Approve via web view.
    approve = client.post(
        "/auth/device",
        data={"user_code": user_code, "action": "approve", "totp": ""},
    )
    assert approve.status_code in (200, 302)

    # First poll after approval returns the cleartext token exactly once.
    granted = Client().post(
        "/api/v1/registry/auth/device-code/poll",
        data={"device_code": device_code},
        content_type="application/json",
    )
    assert granted.status_code == 200
    body = granted.json()
    assert body["token"].startswith("speccify_")

    # Second poll yields denied (consumed).
    after = Client().post(
        "/api/v1/registry/auth/device-code/poll",
        data={"device_code": device_code},
        content_type="application/json",
    )
    assert after.json() == {"status": "denied"}


def test_poll_expired_code() -> None:
    dc = device_codes.issue()
    dc.expires_at = timezone.now() - timedelta(seconds=1)
    dc.save(update_fields=["expires_at"])

    response = Client().post(
        "/api/v1/registry/auth/device-code/poll",
        data={"device_code": dc.device_code},
        content_type="application/json",
    )
    assert response.json() == {"status": "expired"}

    dc.refresh_from_db()
    assert dc.status == DeviceCodeStatus.EXPIRED


def test_poll_unknown_device_code_returns_404() -> None:
    response = Client().post(
        "/api/v1/registry/auth/device-code/poll",
        data={"device_code": "nope-not-real"},
        content_type="application/json",
    )
    assert response.status_code == 404


def test_poll_requires_device_code_in_body() -> None:
    response = Client().post(
        "/api/v1/registry/auth/device-code/poll",
        data={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_deny_via_web_view() -> None:
    User = get_user_model()
    user = User.objects.create_user(username="marc", password="pw-12345678")
    client = Client()
    client.force_login(user)
    start = client.post("/api/v1/registry/auth/device-code").json()

    client.post(
        "/auth/device",
        data={"user_code": start["user_code"], "action": "deny", "totp": ""},
    )

    dc = DeviceCode.objects.get(device_code=start["device_code"])
    assert dc.status == DeviceCodeStatus.DENIED
