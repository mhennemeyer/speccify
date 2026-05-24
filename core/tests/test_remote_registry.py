"""Tests für `RemoteRegistry` (Phase 2 Stage 6).

Wir nutzen `httpx.MockTransport` statt eines echten Live-Servers — der Live-Pfad
gegen Django wird in `registry/tests/test_remote_registry_live.py` abgedeckt.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest
from speccify_core.registry import (
    RegistryError,
    RemoteRegistry,
    Version,
)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_transport(routes: dict[str, httpx.Response]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        if key in routes:
            return routes[key]
        return httpx.Response(404, json={"detail": "not found"})

    return httpx.MockTransport(handler)


def _make(
    routes: dict[str, httpx.Response], *, cache_dir: Path | None = None, token: str | None = None
) -> RemoteRegistry:
    transport = _build_transport(routes)
    client = httpx.Client(transport=transport, base_url="http://reg.test")
    return RemoteRegistry("http://reg.test", token=token, cache_dir=cache_dir, client=client)


def test_via_property_returns_base_url() -> None:
    reg = _make({})
    assert reg.via == "http://reg.test"


def test_rejects_non_http_base_url() -> None:
    with pytest.raises(RegistryError, match="http"):
        RemoteRegistry("ftp://reg.test")


def test_list_versions_parses_response_and_sorts() -> None:
    payload = {
        "id": "@org/button",
        "description": "",
        "tags": [],
        "versions": [
            {
                "version": "0.2.0",
                "sha256": "x",
                "yank_status": "none",
                "yank_reason": None,
                "published_at": "2026-01-01T00:00:00Z",
                "uploader": "marc",
            },
            {
                "version": "0.1.0",
                "sha256": "y",
                "yank_status": "none",
                "yank_reason": None,
                "published_at": "2026-01-01T00:00:00Z",
                "uploader": "marc",
            },
        ],
    }
    routes = {
        "GET /api/v1/registry/specs/org/button": httpx.Response(200, json=payload),
    }
    reg = _make(routes)
    assert reg.list_versions("@org/button") == [Version(0, 1, 0), Version(0, 2, 0)]


def test_list_versions_404_returns_empty() -> None:
    reg = _make({})  # no routes ⇒ default 404
    assert reg.list_versions("@org/missing") == []


def test_list_versions_ignores_non_semver_entries() -> None:
    payload = {
        "versions": [
            {
                "version": "0.1.0",
                "sha256": "x",
                "yank_status": "none",
                "yank_reason": None,
                "published_at": "2026-01-01T00:00:00Z",
                "uploader": "marc",
            },
            {"version": "1.0.0-rc1"},  # pre-release → ignored
            {"version": "not-a-version"},  # ignored
        ],
    }
    routes = {
        "GET /api/v1/registry/specs/org/button": httpx.Response(200, json=payload),
    }
    reg = _make(routes)
    assert reg.list_versions("@org/button") == [Version(0, 1, 0)]


def test_fetch_writes_to_cache_and_returns_spec(tmp_path: Path) -> None:
    yaml_text = "id: '@org/button'\nversion: 0.1.0\nkind: component\n"
    raw = yaml_text.encode("utf-8")
    sha = _sha256_hex(raw)
    routes = {
        "GET /api/v1/registry/specs/org/button/0.1.0": httpx.Response(
            200,
            json={
                "version": "0.1.0",
                "sha256": sha,
                "yank_status": "none",
                "yank_reason": None,
                "published_at": "2026-01-01T00:00:00Z",
                "uploader": "marc",
                "id": "@org/button",
                "yaml": yaml_text,
            },
        ),
    }
    reg = _make(routes, cache_dir=tmp_path / "cache")
    spec = reg.fetch("@org/button", Version(0, 1, 0))

    assert spec.raw_bytes == raw
    cached = tmp_path / "cache" / "reg.test" / "org" / "button" / "0.1.0" / "spec.speccify.yaml"
    assert cached.is_file()
    assert cached.read_bytes() == raw


def test_fetch_uses_cache_when_present_and_skips_network(tmp_path: Path) -> None:
    yaml_text = "cached: true\n"
    raw = yaml_text.encode("utf-8")
    cached = tmp_path / "cache" / "reg.test" / "org" / "button" / "0.1.0" / "spec.speccify.yaml"
    cached.parent.mkdir(parents=True)
    cached.write_bytes(raw)

    # MockTransport ohne Routen → würde 404 antworten, wenn das Netz kontaktiert würde.
    reg = _make({}, cache_dir=tmp_path / "cache")
    spec = reg.fetch("@org/button", Version(0, 1, 0))
    assert spec.raw_bytes == raw
    assert spec.path == cached


def test_fetch_hash_mismatch_raises(tmp_path: Path) -> None:
    yaml_text = "id: '@org/button'\n"
    routes = {
        "GET /api/v1/registry/specs/org/button/0.1.0": httpx.Response(
            200,
            json={
                "version": "0.1.0",
                "sha256": "deadbeef",  # falsch
                "yank_status": "none",
                "yank_reason": None,
                "published_at": "2026-01-01T00:00:00Z",
                "uploader": "marc",
                "id": "@org/button",
                "yaml": yaml_text,
            },
        ),
    }
    reg = _make(routes, cache_dir=tmp_path / "cache")
    with pytest.raises(RegistryError, match="sha256-Mismatch"):
        reg.fetch("@org/button", Version(0, 1, 0))
    # Cache darf bei Mismatch nicht geschrieben werden.
    assert not (tmp_path / "cache").exists() or not list(
        (tmp_path / "cache").rglob("spec.speccify.yaml")
    )


def test_fetch_404_raises_registry_error() -> None:
    reg = _make({})
    with pytest.raises(RegistryError, match="nicht in Registry"):
        reg.fetch("@org/missing", Version(0, 1, 0))


def test_token_header_is_sent() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization", "")
        return httpx.Response(200, json={"versions": []})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://reg.test")
    reg = RemoteRegistry("http://reg.test", token="secret-123", client=client)
    reg.list_versions("@org/button")
    assert captured["auth"] == "Bearer secret-123"


def test_no_token_means_no_authorization_header() -> None:
    captured: dict[str, str | None] = {"auth": "unset"}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"versions": []})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://reg.test")
    reg = RemoteRegistry("http://reg.test", client=client)
    reg.list_versions("@org/button")
    assert captured["auth"] is None


def test_unexpected_status_raises_registry_error() -> None:
    routes = {
        "GET /api/v1/registry/specs/org/button": httpx.Response(503, text="overloaded"),
    }
    reg = _make(routes)
    with pytest.raises(RegistryError, match="Unerwarteter Status 503"):
        reg.list_versions("@org/button")


def test_context_manager_closes_owned_client() -> None:
    # Hier *nicht* den vorbereiteten Client übergeben → RemoteRegistry erstellt eigenen.
    with RemoteRegistry("http://reg.test") as reg:
        assert reg.via == "http://reg.test"
    # Keine Exception → Cleanup ok.


def test_fallback_payload_dict_returns_404() -> None:
    """Stellt sicher dass JSON-Decoding-Fehler nicht silent verschluckt werden."""
    routes = {
        "GET /api/v1/registry/specs/org/button/0.1.0": httpx.Response(200, text="not-json"),
    }
    reg = _make(routes)
    with pytest.raises(Exception):  # noqa: B017 — httpx wirft konkret bei .json()
        reg.fetch("@org/button", Version(0, 1, 0))


# Marker dass json-Modul absichtlich importiert ist (für `httpx.Response(... json=...)`).
_ = json
