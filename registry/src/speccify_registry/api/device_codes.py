"""Issuance, lookup and state transitions for the device-code flow."""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import DeviceCode, DeviceCodeStatus

_USER_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


def _generate_device_code() -> str:
    return secrets.token_urlsafe(32)


def _generate_user_code() -> str:
    raw = "".join(secrets.choice(_USER_CODE_ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def issue() -> DeviceCode:
    ttl = timedelta(seconds=settings.SPECCIFY_DEVICE_CODE_TTL_SECONDS)
    return DeviceCode.objects.create(
        device_code=_generate_device_code(),
        user_code=_generate_user_code(),
        status=DeviceCodeStatus.PENDING,
        expires_at=timezone.now() + ttl,
    )


def _refresh_expiry(dc: DeviceCode) -> DeviceCode:
    """If pending past expiry, flip to ``expired`` and persist."""

    if dc.status == DeviceCodeStatus.PENDING and dc.expires_at <= timezone.now():
        dc.status = DeviceCodeStatus.EXPIRED
        dc.save(update_fields=["status"])
    return dc


def fetch_by_user_code(user_code: str) -> DeviceCode | None:
    try:
        dc = DeviceCode.objects.get(user_code=user_code.upper())
    except DeviceCode.DoesNotExist:
        return None
    return _refresh_expiry(dc)


def fetch_by_device_code(device_code: str) -> DeviceCode | None:
    try:
        dc = DeviceCode.objects.get(device_code=device_code)
    except DeviceCode.DoesNotExist:
        return None
    return _refresh_expiry(dc)


def approve(dc: DeviceCode, *, user, api_token) -> DeviceCode:
    dc.status = DeviceCodeStatus.APPROVED
    dc.user = user
    dc.api_token = api_token
    dc.save(update_fields=["status", "user", "api_token"])
    return dc


def deny(dc: DeviceCode) -> DeviceCode:
    dc.status = DeviceCodeStatus.DENIED
    dc.save(update_fields=["status"])
    return dc


def consume(dc: DeviceCode) -> DeviceCode:
    dc.status = DeviceCodeStatus.CONSUMED
    dc.save(update_fields=["status"])
    return dc
