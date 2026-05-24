"""Stage-1 smoke tests for the registry HTTP surface."""

from __future__ import annotations

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_whoami_anonymous_returns_401() -> None:
    response = Client().get("/api/v1/registry/whoami")
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_specs_search_empty_registry() -> None:
    response = Client().get("/api/v1/registry/specs?q=foo")
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["total"] == 0
    assert body["limit"] == 20
    assert body["offset"] == 0


def test_unknown_route_returns_404() -> None:
    response = Client().get("/api/v1/registry/does-not-exist")
    assert response.status_code == 404
