"""Tests for the publish/fetch/versions REST endpoints."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from speccify_registry.api.models import (
    ApiToken,
    Scope,
    ScopeReservation,
    SpecVersion,
)
from speccify_registry.api.tokens import mint_token

pytestmark = pytest.mark.django_db


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


def _publish(client: Client, token: str, yaml_bytes: bytes):
    return client.post(
        "/api/v1/registry/specs/publish",
        data=json.dumps({"yaml": yaml_bytes.decode("utf-8")}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


def test_publish_creates_scope_spec_and_version() -> None:
    user, minted = _make_user_with_token()

    response = _publish(Client(), minted.cleartext, _VALID_SPEC)
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["id"] == "@org/button"
    assert body["version"] == "0.1.0"
    assert body["created"] is True
    assert body["yank_status"] == "none"

    scope = Scope.objects.get(name="org")
    assert scope.owner_id == user.id
    sv = SpecVersion.objects.get(spec__scope__name="org", spec__name="button")
    assert sv.version == "0.1.0"
    assert bytes(sv.yaml_bytes) == _VALID_SPEC


def test_publish_idempotent_on_identical_bytes() -> None:
    _, minted = _make_user_with_token()
    client = Client()

    first = _publish(client, minted.cleartext, _VALID_SPEC)
    assert first.status_code == 201
    second = _publish(client, minted.cleartext, _VALID_SPEC)
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert SpecVersion.objects.count() == 1


def test_publish_conflict_on_byte_drift() -> None:
    _, minted = _make_user_with_token()
    client = Client()

    _publish(client, minted.cleartext, _VALID_SPEC)
    drifted = _VALID_SPEC.replace(b"A clickable thing.", b"Drifted summary.")
    response = _publish(client, minted.cleartext, drifted)
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "version_conflict"


def test_publish_requires_authentication() -> None:
    response = Client().post(
        "/api/v1/registry/specs/publish",
        data=json.dumps({"yaml": _VALID_SPEC.decode("utf-8")}),
        content_type="application/json",
    )
    assert response.status_code == 401


def test_publish_rejects_stale_2fa() -> None:
    _, minted = _make_user_with_token(fresh_2fa=False)
    response = _publish(Client(), minted.cleartext, _VALID_SPEC)
    assert response.status_code == 403
    assert response.json()["code"] == "stale_2fa"


def test_publish_rejects_invalid_yaml() -> None:
    _, minted = _make_user_with_token()
    response = _publish(Client(), minted.cleartext, b": : not yaml :")
    assert response.status_code == 400
    assert response.json()["code"] in ("invalid_yaml", "schema_violation")


def test_publish_rejects_schema_violation() -> None:
    _, minted = _make_user_with_token()
    # Missing required fields.
    response = _publish(Client(), minted.cleartext, b"id: '@org/x'\nversion: 0.1.0\n")
    assert response.status_code == 400
    assert response.json()["code"] == "schema_violation"


def test_publish_blocks_reserved_scope() -> None:
    _, minted = _make_user_with_token()
    ScopeReservation.objects.create(name="admin", reason="reserved")
    yaml_bytes = _VALID_SPEC.replace(b"@org/button", b"@admin/button")
    response = _publish(Client(), minted.cleartext, yaml_bytes)
    assert response.status_code == 403
    assert response.json()["code"] == "scope_reserved"


def test_publish_blocks_scope_owned_by_another_user() -> None:
    other = get_user_model().objects.create_user(username="alice", password="pw-12345678")
    Scope.objects.create(name="org", owner=other)

    _, minted = _make_user_with_token(username="marc")
    response = _publish(Client(), minted.cleartext, _VALID_SPEC)
    assert response.status_code == 403
    assert response.json()["code"] == "scope_forbidden"


def test_publish_rejects_missing_yaml_payload() -> None:
    _, minted = _make_user_with_token()
    response = Client().post(
        "/api/v1/registry/specs/publish",
        data=json.dumps({}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {minted.cleartext}",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "missing_yaml"


def test_versions_endpoint_lists_published_versions() -> None:
    _, minted = _make_user_with_token()
    client = Client()
    _publish(client, minted.cleartext, _VALID_SPEC)
    _publish(
        client,
        minted.cleartext,
        _VALID_SPEC.replace(b"0.1.0", b"0.1.1"),
    )

    response = Client().get("/api/v1/registry/specs/org/button")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "@org/button"
    versions = [v["version"] for v in body["versions"]]
    assert sorted(versions) == ["0.1.0", "0.1.1"]


def test_versions_endpoint_404_on_unknown_spec() -> None:
    response = Client().get("/api/v1/registry/specs/org/nope")
    assert response.status_code == 404


def test_version_detail_returns_bytes_and_hash() -> None:
    _, minted = _make_user_with_token()
    publish_response = _publish(Client(), minted.cleartext, _VALID_SPEC)
    expected_hash = publish_response.json()["sha256"]

    response = Client().get("/api/v1/registry/specs/org/button/0.1.0")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "@org/button"
    assert body["version"] == "0.1.0"
    assert body["sha256"] == expected_hash
    assert body["yaml"].encode("utf-8") == _VALID_SPEC


def test_publish_via_multipart_upload() -> None:
    from io import BytesIO

    _, minted = _make_user_with_token()
    response = Client().post(
        "/api/v1/registry/specs/publish",
        data={"yaml": BytesIO(_VALID_SPEC)},
        HTTP_AUTHORIZATION=f"Bearer {minted.cleartext}",
    )
    assert response.status_code == 201
    sv = SpecVersion.objects.get()
    assert bytes(sv.yaml_bytes) == _VALID_SPEC


def test_revoked_token_cannot_publish() -> None:
    _, minted = _make_user_with_token()
    ApiToken.objects.filter(id=minted.token.id).update(revoked_at=timezone.now())
    response = _publish(Client(), minted.cleartext, _VALID_SPEC)
    assert response.status_code == 401
