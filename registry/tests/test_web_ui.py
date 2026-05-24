"""Tests for the server-rendered browse Web-UI (Stage 4)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from speccify_registry.api.models import Scope, Spec, SpecVersion

pytestmark = pytest.mark.django_db


def _seed_spec(
    *,
    owner_username: str,
    scope_name: str,
    name: str,
    description: str = "",
    tags: list[str] | None = None,
    versions: list[str] | None = None,
    minutes_ago: int = 0,
) -> Spec:
    User = get_user_model()
    user, _ = User.objects.get_or_create(username=owner_username)
    scope, _ = Scope.objects.get_or_create(name=scope_name, defaults={"owner": user})
    spec = Spec.objects.create(scope=scope, name=name, description=description, tags=tags or [])
    base = timezone.now() - timedelta(minutes=minutes_ago)
    for i, v in enumerate(versions or ["0.1.0"]):
        yaml_bytes = f'id: "@{scope_name}/{name}"\nversion: {v}\n'.encode()
        sv = SpecVersion.objects.create(
            spec=spec,
            version=v,
            yaml_bytes=yaml_bytes,
            sha256="a" * 64,
            uploader=user,
        )
        SpecVersion.objects.filter(pk=sv.pk).update(published_at=base + timedelta(seconds=i))
    return spec


# --- Home view ---------------------------------------------------------


def test_home_renders_for_anonymous_visitor() -> None:
    response = Client().get("/")
    assert response.status_code == 200
    assert b"Browse specs" in response.content


def test_home_lists_published_specs_with_link_to_detail() -> None:
    _seed_spec(owner_username="alice", scope_name="org", name="button")
    response = Client().get("/")
    assert response.status_code == 200
    assert b"@org/button" in response.content
    assert b"/specs/org/button" in response.content


def test_home_filters_via_query_param() -> None:
    _seed_spec(owner_username="alice", scope_name="org", name="button")
    _seed_spec(owner_username="alice", scope_name="org", name="toggle")
    response = Client().get("/?q=butt")
    assert response.status_code == 200
    assert b"@org/button" in response.content
    assert b"@org/toggle" not in response.content


def test_home_orders_by_latest_published_desc() -> None:
    _seed_spec(owner_username="alice", scope_name="org", name="old", minutes_ago=60)
    _seed_spec(owner_username="alice", scope_name="org", name="new", minutes_ago=1)
    response = Client().get("/")
    body = response.content.decode()
    assert body.index("@org/new") < body.index("@org/old")


def test_home_excludes_specs_without_versions() -> None:
    User = get_user_model()
    u = User.objects.create(username="ghost")
    scope = Scope.objects.create(name="ghost", owner=u)
    Spec.objects.create(scope=scope, name="empty")
    response = Client().get("/")
    assert b"@ghost/empty" not in response.content


# --- Spec detail view --------------------------------------------------


def test_spec_detail_renders_versions_and_yaml() -> None:
    _seed_spec(
        owner_username="alice",
        scope_name="org",
        name="button",
        versions=["0.1.0", "0.1.1"],
    )
    response = Client().get("/specs/org/button")
    assert response.status_code == 200
    assert b"@org/button" in response.content
    assert b"0.1.0" in response.content
    assert b"0.1.1" in response.content
    assert b"id: &quot;@org/button&quot;" in response.content
    # Owner link present
    assert b"/u/alice" in response.content


def test_spec_detail_404_for_unknown_spec() -> None:
    response = Client().get("/specs/org/missing")
    assert response.status_code == 404


def test_spec_detail_404_when_no_versions() -> None:
    User = get_user_model()
    u = User.objects.create(username="alice")
    scope = Scope.objects.create(name="org", owner=u)
    Spec.objects.create(scope=scope, name="empty")
    response = Client().get("/specs/org/empty")
    assert response.status_code == 404


# --- User profile view -------------------------------------------------


def test_user_profile_renders_owned_scopes_and_specs() -> None:
    _seed_spec(owner_username="alice", scope_name="alice", name="card")
    _seed_spec(owner_username="alice", scope_name="alice", name="modal")
    _seed_spec(owner_username="bob", scope_name="bob", name="other")
    response = Client().get("/u/alice")
    assert response.status_code == 200
    assert b"@alice" in response.content
    assert b"@alice/card" in response.content
    assert b"@alice/modal" in response.content
    assert b"@bob/other" not in response.content


def test_user_profile_404_for_unknown_user() -> None:
    response = Client().get("/u/nobody")
    assert response.status_code == 404


def test_user_profile_handles_user_without_specs() -> None:
    get_user_model().objects.create(username="lurker")
    response = Client().get("/u/lurker")
    assert response.status_code == 200
    assert b"No specs published yet." in response.content
