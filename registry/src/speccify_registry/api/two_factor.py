"""Thin wrappers around ``django_otp`` for TOTP setup/verify.

Phase-2 Round-1 decision (Q4): TOTP only. WebAuthn stays Phase 6.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice


def get_or_create_unconfirmed_device(user, name: str = "default") -> TOTPDevice:
    """Return an existing un-confirmed TOTP device for ``user`` or create one."""

    device, _created = TOTPDevice.objects.get_or_create(
        user=user, name=name, defaults={"confirmed": False}
    )
    return device


def get_confirmed_device(user) -> TOTPDevice | None:
    return TOTPDevice.objects.filter(user=user, confirmed=True).first()


def verify_token(device: TOTPDevice, token: str) -> bool:
    """Verify a 6-digit TOTP code; on success, mark device as confirmed."""

    ok = bool(device.verify_token(token))
    if ok and not device.confirmed:
        device.confirmed = True
        device.save(update_fields=["confirmed"])
    return ok


def has_fresh_2fa(api_token) -> bool:
    """Return True if ``api_token`` was minted/refreshed inside the TTL window."""

    if not api_token.requires_2fa:
        return True
    last = api_token.last_2fa_verified_at
    if last is None:
        return False
    ttl = timedelta(seconds=settings.SPECCIFY_2FA_TTL_SECONDS)
    return last >= timezone.now() - ttl
