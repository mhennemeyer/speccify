"""Tests for the token mint/verify helpers."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from speccify_registry.api.tokens import mint_token, verify_cleartext

pytestmark = pytest.mark.django_db


def _user(username: str = "marc"):
    return get_user_model().objects.create_user(username=username, password="pw-12345678")


def test_mint_returns_cleartext_and_persists_hash() -> None:
    user = _user()
    minted = mint_token(user=user, label="laptop")

    assert minted.cleartext.startswith("speccify_")
    assert minted.token.token_hash != minted.cleartext
    assert minted.token.token_prefix == minted.cleartext[:12]
    assert minted.token.user_id == user.id


def test_verify_cleartext_happy_path() -> None:
    user = _user()
    minted = mint_token(user=user, label="laptop")

    found = verify_cleartext(minted.cleartext)
    assert found is not None
    assert found.id == minted.token.id
    assert found.last_used_at is not None


def test_verify_cleartext_rejects_unknown_token() -> None:
    _user()
    assert verify_cleartext("speccify_completelybogusvalue123456") is None


def test_verify_cleartext_rejects_revoked_token() -> None:
    from django.utils import timezone

    user = _user()
    minted = mint_token(user=user, label="laptop")
    minted.token.revoked_at = timezone.now()
    minted.token.save(update_fields=["revoked_at"])

    assert verify_cleartext(minted.cleartext) is None


def test_verify_cleartext_rejects_non_speccify_format() -> None:
    assert verify_cleartext("ghp_someothertokenformat") is None
