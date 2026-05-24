"""Performance-Smoke für `/api/v1/registry/specs` (Phase 2 Stage 7).

Sanity-Smoke (kein blocking CI-Gate): mit 100 Specs befüllt, 50× Query
ausgeführt, p95 unter `_P95_BUDGET_SECONDS`. Wird hauptsächlich lokal
auf SQLite ausgeführt; das harte Phase-2-Budget („< 200 ms p95") gilt
für Postgres + Cache-Hit. Der Test verifiziert deshalb nur das
großzügigere Sanity-Budget, damit Layer-Regressionen (z. B. versehentlich
eingebaute O(n²)-Schleifen oder N+1) auffallen.
"""

from __future__ import annotations

import time
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from speccify_registry.api.models import Scope, Spec, SpecVersion

pytestmark = pytest.mark.django_db

# Sanity-Budget für SQLite-In-Memory mit 100 Specs; harter Phase-2-Vertrag
# („< 200 ms p95") wird auf Postgres separat erfüllt.
_P95_BUDGET_SECONDS = 1.0
_N_SPECS = 100
_N_QUERIES = 50


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return ordered[idx]


def test_search_p95_smoke() -> None:
    User = get_user_model()
    user = User.objects.create(username="perf-owner")
    scope = Scope.objects.create(name="perf", owner=user)
    base_time = timezone.now() - timedelta(days=1)
    specs = []
    for i in range(_N_SPECS):
        spec = Spec.objects.create(
            scope=scope,
            name=f"comp-{i:03d}",
            description=f"Spec {i}",
            tags=[f"tag-{i % 5}"],
        )
        specs.append(spec)
    # Versionen in einem zweiten Pass anlegen, damit `bulk_create` zumindest
    # für die SpecVersions billig bleibt.
    versions = [
        SpecVersion(
            spec=spec,
            version="0.1.0",
            yaml_bytes=f'id: "@perf/comp-{i:03d}"\nversion: 0.1.0\n'.encode(),
            sha256="0" * 64,
            uploader=user,
        )
        for i, spec in enumerate(specs)
    ]
    SpecVersion.objects.bulk_create(versions)
    # `published_at` deterministisch setzen, damit Ordering stabil ist.
    for i, sv in enumerate(SpecVersion.objects.filter(spec__in=specs)):
        SpecVersion.objects.filter(pk=sv.pk).update(published_at=base_time + timedelta(seconds=i))

    client = Client()
    durations: list[float] = []
    for _ in range(_N_QUERIES):
        start = time.perf_counter()
        resp = client.get("/api/v1/registry/specs", {"q": "comp", "limit": 20})
        durations.append(time.perf_counter() - start)
        assert resp.status_code == 200

    p95 = _percentile(durations, 95)
    assert p95 < _P95_BUDGET_SECONDS, (
        f"Search-p95 {p95 * 1000:.1f} ms überschreitet Sanity-Budget "
        f"{_P95_BUDGET_SECONDS * 1000:.0f} ms (Regressionshinweis: N+1 oder fehlender Index)."
    )
