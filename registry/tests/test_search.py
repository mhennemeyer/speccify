"""Tests for the ``GET /api/v1/registry/specs`` search endpoint."""

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
    scope_name: str,
    name: str,
    description: str = "",
    tags: list[str] | None = None,
    versions: list[str] | None = None,
    minutes_ago: int = 0,
    owner_username: str | None = None,
) -> Spec:
    User = get_user_model()
    owner_username = owner_username or f"u-{scope_name}"
    user, _ = User.objects.get_or_create(username=owner_username)
    scope, _ = Scope.objects.get_or_create(name=scope_name, defaults={"owner": user})
    spec = Spec.objects.create(
        scope=scope,
        name=name,
        description=description,
        tags=tags or [],
    )
    base = timezone.now() - timedelta(minutes=minutes_ago)
    for i, v in enumerate(versions or ["0.1.0"]):
        sv = SpecVersion.objects.create(
            spec=spec,
            version=v,
            yaml_bytes=f'id: "@{scope_name}/{name}"\nversion: {v}\n'.encode(),
            sha256="0" * 64,
            uploader=user,
        )
        # ``published_at`` uses ``auto_now_add``; override deterministically
        # so ordering assertions are stable across the suite.
        SpecVersion.objects.filter(pk=sv.pk).update(published_at=base + timedelta(seconds=i))
    return spec


def _search(client: Client, **params) -> dict:
    response = client.get("/api/v1/registry/specs", params)
    assert response.status_code == 200, response.content
    return response.json()


def test_search_returns_empty_when_no_specs() -> None:
    body = _search(Client())
    assert body == {"results": [], "total": 0, "limit": 20, "offset": 0}


def test_search_excludes_specs_without_versions() -> None:
    User = get_user_model()
    user = User.objects.create(username="ghost")
    scope = Scope.objects.create(name="ghost", owner=user)
    Spec.objects.create(scope=scope, name="empty", description="", tags=[])

    body = _search(Client())
    assert body["total"] == 0
    assert body["results"] == []


def test_search_orders_by_latest_published_at_desc() -> None:
    _seed_spec(scope_name="org", name="old", minutes_ago=120)
    _seed_spec(scope_name="org", name="new", minutes_ago=1)
    _seed_spec(scope_name="org", name="mid", minutes_ago=30)

    body = _search(Client())
    ids = [r["id"] for r in body["results"]]
    assert ids == ["@org/new", "@org/mid", "@org/old"]
    assert body["total"] == 3


def test_search_returns_latest_version_string() -> None:
    _seed_spec(
        scope_name="org",
        name="button",
        versions=["0.1.0", "0.1.1", "0.2.0"],
    )
    body = _search(Client())
    assert len(body["results"]) == 1
    row = body["results"][0]
    assert row["id"] == "@org/button"
    assert row["latest_version"] == "0.2.0"
    assert row["latest_published_at"]


def test_search_filters_by_query_in_name() -> None:
    _seed_spec(scope_name="org", name="button")
    _seed_spec(scope_name="org", name="toggle")

    body = _search(Client(), q="butt")
    assert [r["id"] for r in body["results"]] == ["@org/button"]
    assert body["total"] == 1


def test_search_filters_by_query_in_description_case_insensitive() -> None:
    _seed_spec(scope_name="org", name="a", description="Clickable Element")
    _seed_spec(scope_name="org", name="b", description="Unrelated")

    body = _search(Client(), q="clickable")
    assert [r["id"] for r in body["results"]] == ["@org/a"]


def test_search_filters_by_tag_substring() -> None:
    _seed_spec(scope_name="org", name="a", tags=["form", "input"])
    _seed_spec(scope_name="org", name="b", tags=["layout"])

    body = _search(Client(), q="form")
    assert [r["id"] for r in body["results"]] == ["@org/a"]


def test_search_filters_by_scope() -> None:
    _seed_spec(scope_name="org", name="a")
    _seed_spec(scope_name="alice", name="b")

    body = _search(Client(), scope="alice")
    assert [r["id"] for r in body["results"]] == ["@alice/b"]
    assert body["total"] == 1


def test_search_pagination_limit_and_offset() -> None:
    for i in range(5):
        _seed_spec(scope_name="org", name=f"s{i}", minutes_ago=100 - i)

    first = _search(Client(), limit=2)
    assert len(first["results"]) == 2
    assert first["total"] == 5
    assert first["limit"] == 2
    assert first["offset"] == 0

    second = _search(Client(), limit=2, offset=2)
    assert len(second["results"]) == 2
    assert second["offset"] == 2
    # No overlap between page 1 and page 2.
    assert {r["id"] for r in first["results"]} & {r["id"] for r in second["results"]} == set()


def test_search_caps_limit_at_max() -> None:
    body = _search(Client(), limit=500)
    assert body["limit"] == 100


def test_search_rejects_negative_offset() -> None:
    response = Client().get("/api/v1/registry/specs", {"offset": -1})
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_pagination"


def test_search_rejects_non_integer_limit() -> None:
    response = Client().get("/api/v1/registry/specs", {"limit": "abc"})
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_pagination"


def test_search_response_shape_matches_contract() -> None:
    _seed_spec(
        scope_name="org",
        name="button",
        description="Clickable thing.",
        tags=["form"],
    )
    body = _search(Client())
    row = body["results"][0]
    assert set(row.keys()) == {
        "id",
        "scope",
        "name",
        "description",
        "tags",
        "latest_version",
        "latest_published_at",
    }
    assert row["scope"] == "org"
    assert row["name"] == "button"
    assert row["tags"] == ["form"]
