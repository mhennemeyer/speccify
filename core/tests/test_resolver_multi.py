"""Tests für Multi-Registry-Resolver (Phase 2 Stage 6).

Wir bauen eine ``FakeRegistry`` als In-Memory-Implementation des ``Registry``-Protocols,
um Cross-Registry-Szenarien ohne FS- oder HTTP-Setup zu prüfen.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from speccify_core.manifest import ProjectManifest
from speccify_core.registry import Spec, Version
from speccify_core.resolver import (
    Resolver,
    ScopeRegistryConflictError,
    VersionNotFoundError,
)


class FakeRegistry:
    """In-Memory-``Registry`` für Tests."""

    def __init__(self, via: str, specs: dict[str, dict[str, bytes]]) -> None:
        # specs: {spec_id: {version_str: raw_bytes}}
        self._via = via
        self._specs = specs

    @property
    def via(self) -> str:
        return self._via

    def list_versions(self, spec_id: str) -> list[Version]:
        if spec_id not in self._specs:
            return []
        return sorted(Version.parse(v) for v in self._specs[spec_id].keys())

    def fetch(self, spec_id: str, version: Version) -> Spec:
        raw = self._specs[spec_id][str(version)]
        return Spec(spec_id=spec_id, version=version, raw_bytes=raw, path=Path(f"/fake/{spec_id}"))


def _manifest(deps: dict[str, str], tmp_path: Path) -> ProjectManifest:
    body = "schema_version: 1\ntarget: react\ndependencies:\n" + "".join(
        f"  {k!r}: {v!r}\n" for k, v in deps.items()
    )
    path = tmp_path / "speccify.yaml"
    path.write_text(body, encoding="utf-8")
    return ProjectManifest.load(path)


def _spec_bytes(spec_id: str, version: str) -> bytes:
    return (
        f"id: '{spec_id}'\nversion: {version}\nkind: component\ntitle: t\nsummary: s\n"
    ).encode()


def test_two_registries_resolve_from_first_match(tmp_path: Path) -> None:
    """Zwei Registries, verschiedene Scopes — jede liefert ihr Set."""
    local = FakeRegistry(
        "registry-fixtures",
        {"@org/button": {"0.1.0": _spec_bytes("@org/button", "0.1.0")}},
    )
    remote = FakeRegistry(
        "http://registry.example",
        {"@acme/widget": {"0.2.0": _spec_bytes("@acme/widget", "0.2.0")}},
    )
    m = _manifest({"@org/button": "^0.1", "@acme/widget": "^0.2"}, tmp_path)

    graph = Resolver([local, remote]).resolve(m)
    via_by_id = {r.spec_id: r.via for r in graph.resolutions}
    assert via_by_id == {
        "@org/button": "registry-fixtures",
        "@acme/widget": "http://registry.example",
    }


def test_remote_only_resolve_writes_url_via(tmp_path: Path) -> None:
    remote = FakeRegistry(
        "http://registry.example",
        {"@org/button": {"0.1.0": _spec_bytes("@org/button", "0.1.0")}},
    )
    m = _manifest({"@org/button": "^0.1"}, tmp_path)

    graph = Resolver([remote]).resolve(m)
    assert len(graph.resolutions) == 1
    assert graph.resolutions[0].via == "http://registry.example"
    assert (
        graph.resolutions[0].spec_sha256
        == "sha256:" + hashlib.sha256(_spec_bytes("@org/button", "0.1.0")).hexdigest()
    )


def test_scope_conflict_when_two_registries_offer_same_scope(tmp_path: Path) -> None:
    """Beide Registries bieten ``@org`` — harter Fehler (Dependency-Confusion-Schutz)."""
    a = FakeRegistry(
        "registry-fixtures",
        {"@org/button": {"0.1.0": _spec_bytes("@org/button", "0.1.0")}},
    )
    b = FakeRegistry(
        "http://attacker.example",
        {"@org/button": {"9.9.9": _spec_bytes("@org/button", "9.9.9")}},
    )
    m = _manifest({"@org/button": "^0.1"}, tmp_path)

    with pytest.raises(ScopeRegistryConflictError, match="@org"):
        Resolver([a, b]).resolve(m)


def test_scope_conflict_across_transitive_deps(tmp_path: Path) -> None:
    """Erste Registry bedient ``@org/foo``, zweite hätte zweite Spec für ``@org/bar`` —
    auch das ist ein Cross-Registry-Konflikt, weil derselbe Scope gemeint ist."""
    a = FakeRegistry(
        "registry-fixtures",
        {"@org/foo": {"0.1.0": _spec_bytes("@org/foo", "0.1.0")}},
    )
    b = FakeRegistry(
        "http://other.example",
        {"@org/bar": {"0.1.0": _spec_bytes("@org/bar", "0.1.0")}},
    )
    m = _manifest({"@org/foo": "^0.1", "@org/bar": "^0.1"}, tmp_path)

    with pytest.raises(ScopeRegistryConflictError, match="@org"):
        Resolver([a, b]).resolve(m)


def test_missing_spec_raises_version_not_found(tmp_path: Path) -> None:
    a = FakeRegistry(
        "registry-fixtures",
        {"@org/button": {"0.1.0": _spec_bytes("@org/button", "0.1.0")}},
    )
    m = _manifest({"@org/missing": "^0.1"}, tmp_path)
    with pytest.raises(VersionNotFoundError):
        Resolver([a]).resolve(m)


def test_single_registry_backward_compat_accepts_local_directly(tmp_path: Path) -> None:
    """``Resolver(LocalRegistry(...))`` muss weiterhin akzeptiert werden."""
    a = FakeRegistry(
        "registry-fixtures",
        {"@org/button": {"0.1.0": _spec_bytes("@org/button", "0.1.0")}},
    )
    m = _manifest({"@org/button": "^0.1"}, tmp_path)
    graph = Resolver(a).resolve(m)  # nicht in Liste verpackt
    assert len(graph.resolutions) == 1


def test_empty_registry_list_raises() -> None:
    from speccify_core.resolver import ResolverError

    with pytest.raises(ResolverError, match="mindestens eine Registry"):
        Resolver([])
