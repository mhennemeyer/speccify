"""Step-0 smoke test: app factory builds and healthcheck responds."""

from __future__ import annotations

from fastapi.testclient import TestClient
from speccify_web_backend.app import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
