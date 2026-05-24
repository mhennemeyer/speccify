"""Tests for the Stage-1 registry models."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from speccify_registry.api.models import (
    ApiToken,
    Scope,
    ScopeReservation,
    Spec,
    SpecVersion,
    YankStatus,
)

pytestmark = pytest.mark.django_db


def _make_user(username: str = "marc") -> object:
    User = get_user_model()
    return User.objects.create_user(username=username, password="pw-12345678")


def test_scope_unique_name() -> None:
    user = _make_user()
    Scope.objects.create(name="org", owner=user)
    with pytest.raises(IntegrityError):
        Scope.objects.create(name="org", owner=user)


def test_spec_unique_per_scope() -> None:
    user = _make_user()
    scope = Scope.objects.create(name="org", owner=user)
    Spec.objects.create(scope=scope, name="button")
    with pytest.raises(IntegrityError):
        Spec.objects.create(scope=scope, name="button")


def test_spec_version_unique_and_yank_default() -> None:
    user = _make_user()
    scope = Scope.objects.create(name="org", owner=user)
    spec = Spec.objects.create(scope=scope, name="button")
    version = SpecVersion.objects.create(
        spec=spec,
        version="0.1.0",
        yaml_bytes=b"id: spec://org/button\n",
        sha256="a" * 64,
        uploader=user,
    )

    # Default yank status is "none".
    assert version.yank_status == YankStatus.NONE
    assert version.yank_reason == ""

    with pytest.raises(IntegrityError):
        SpecVersion.objects.create(
            spec=spec,
            version="0.1.0",
            yaml_bytes=b"id: spec://org/button\n",
            sha256="b" * 64,
            uploader=user,
        )


def test_api_token_does_not_persist_plaintext() -> None:
    """The model only stores a hashed token — no plaintext column."""

    user = _make_user()
    token = ApiToken.objects.create(
        user=user,
        label="cli@laptop",
        token_hash="argon2$dummyhash",
    )

    # No attribute on the model that holds the cleartext token.
    assert not hasattr(token, "token")
    assert not hasattr(token, "token_plain")
    assert token.token_hash.startswith("argon2$")


def test_scope_reservation_unique() -> None:
    ScopeReservation.objects.create(name="admin", reason="reserved")
    with pytest.raises(IntegrityError):
        ScopeReservation.objects.create(name="admin", reason="dup")
