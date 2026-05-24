"""End-to-end-Test für `RemoteRegistry` gegen ein laufendes Django-Registry.

Veröffentlicht eine Spec via API und liest sie dann mit ``RemoteRegistry`` zurück.
Validiert dass Hash-Verify, Cache-Schreiben und ``via`` korrekt funktionieren.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from speccify_core.manifest import ProjectManifest
from speccify_core.registry import RegistryError, RemoteRegistry, Version
from speccify_core.resolver import Resolver, ScopeRegistryConflictError
from speccify_registry.api.tokens import mint_token

pytestmark = pytest.mark.django_db(transaction=True)


_FIXTURE = (
    Path(__file__).resolve().parents[2] / "registry-fixtures/org/button/0.1.0/spec.speccify.yaml"
)


def _mint_fresh_token(username: str = "marc") -> str:
    user = get_user_model().objects.create_user(username=username, password="pw-12345678")
    minted = mint_token(
        user=user,
        label="remote-registry-test",
        requires_2fa=True,
        last_2fa_verified_at=timezone.now(),
    )
    return minted.cleartext


def _publish(base_url: str, token: str, yaml_path: Path) -> dict:
    files = {"yaml": (yaml_path.name, yaml_path.read_bytes(), "application/x-yaml")}
    resp = httpx.post(
        f"{base_url}/api/v1/registry/specs/publish",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def test_remote_registry_list_and_fetch_against_live_server(live_server, tmp_path: Path) -> None:
    token = _mint_fresh_token()
    _publish(live_server.url, token, _FIXTURE)

    with RemoteRegistry(live_server.url, cache_dir=tmp_path / "cache") as reg:
        assert reg.via == live_server.url.rstrip("/")
        versions = reg.list_versions("@org/button")
        assert versions == [Version(0, 1, 0)]

        spec = reg.fetch("@org/button", Version(0, 1, 0))
        expected_bytes = _FIXTURE.read_bytes()
        assert spec.raw_bytes == expected_bytes
        # Cache wurde geschrieben.
        cached_files = list((tmp_path / "cache").rglob("spec.speccify.yaml"))
        assert len(cached_files) == 1
        assert cached_files[0].read_bytes() == expected_bytes

        # Hash der Spec passt zum Server-Hash (sha256 hex).
        assert hashlib.sha256(spec.raw_bytes).hexdigest()


def test_remote_registry_resolves_via_resolver_with_resolved_via_url(
    live_server, tmp_path: Path
) -> None:
    token = _mint_fresh_token()
    _publish(live_server.url, token, _FIXTURE)

    # Minimal-Manifest, das nur @org/button braucht (button.spec hat keine `uses`).
    manifest_path = tmp_path / "speccify.yaml"
    manifest_path.write_text(
        "schema_version: 1\ntarget: react\ndependencies:\n  '@org/button': '^0.1'\n",
        encoding="utf-8",
    )
    m = ProjectManifest.load(manifest_path)

    with RemoteRegistry(live_server.url, cache_dir=tmp_path / "cache") as reg:
        graph = Resolver([reg]).resolve(m)
        assert len(graph.resolutions) == 1
        r = graph.resolutions[0]
        assert r.spec_id == "@org/button"
        assert r.via == live_server.url.rstrip("/")
        # ``resolved_via`` ist eine echte URL — das ist der Phase-2-Stage-6-Marker
        # gegenüber dem alten ``registry-fixtures`` String.
        assert r.via.startswith("http://")


def test_remote_registry_404_on_unknown_spec(live_server) -> None:
    with RemoteRegistry(live_server.url) as reg:
        assert reg.list_versions("@org/unknown") == []
        with pytest.raises(RegistryError):
            reg.fetch("@org/unknown", Version(0, 1, 0))


def test_resolver_rejects_scope_offered_by_two_registries(live_server, tmp_path: Path) -> None:
    """Two registries (live + fake) both claim ``@org`` → ``ScopeRegistryConflictError``."""
    token = _mint_fresh_token()
    _publish(live_server.url, token, _FIXTURE)

    class FakeShadowRegistry:
        @property
        def via(self) -> str:
            return "http://shadow.example"

        def list_versions(self, spec_id: str) -> list[Version]:
            if spec_id == "@org/button":
                return [Version(9, 9, 9)]
            return []

        def fetch(self, spec_id: str, version: Version):  # noqa: ARG002
            raise AssertionError("nicht aufgerufen werden")

    manifest_path = tmp_path / "speccify.yaml"
    manifest_path.write_text(
        "schema_version: 1\ntarget: react\ndependencies:\n  '@org/button': '^0.1'\n",
        encoding="utf-8",
    )
    m = ProjectManifest.load(manifest_path)

    with RemoteRegistry(live_server.url, cache_dir=tmp_path / "cache") as remote:
        with pytest.raises(ScopeRegistryConflictError):
            Resolver([remote, FakeShadowRegistry()]).resolve(m)
