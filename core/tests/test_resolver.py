"""Resolver-Tests: Happy-Path, transitiv, Diamond, Konflikte, fehlende Versionen."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import (
    LocalRegistry,
    ProjectManifest,
    Range,
    RangeConflictError,
    Resolver,
    ResolverError,
    Version,
    VersionNotFoundError,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"


def _manifest(deps: dict[str, str], target: str = "react") -> ProjectManifest:
    return ProjectManifest(
        schema_version=1,
        target=target,
        dependencies=deps,
        registry_path=str(FIXTURES),
        source_path=None,
    )


def _registry() -> LocalRegistry:
    return LocalRegistry(FIXTURES)


# ---- Range -----------------------------------------------------------


def test_range_caret_minor_only() -> None:
    r = Range.parse("^0.1")
    assert r.exact is False
    assert r.min_version == Version(0, 1, 0)
    assert r.upper_exclusive == Version(0, 2, 0)
    assert r.contains(Version(0, 1, 5))
    assert not r.contains(Version(0, 2, 0))


def test_range_caret_full() -> None:
    r = Range.parse("^1.2.3")
    assert r.min_version == Version(1, 2, 3)
    assert r.upper_exclusive == Version(2, 0, 0)
    assert r.contains(Version(1, 9, 9))
    assert not r.contains(Version(2, 0, 0))
    assert not r.contains(Version(1, 2, 2))


def test_range_exact() -> None:
    r = Range.parse("0.1.1")
    assert r.exact is True
    assert r.contains(Version(0, 1, 1))
    assert not r.contains(Version(0, 1, 2))


def test_range_invalid() -> None:
    with pytest.raises(ResolverError):
        Range.parse("~0.1")
    with pytest.raises(ResolverError):
        Range.parse("0.1")  # exact braucht patch


# ---- Resolver --------------------------------------------------------


def test_resolver_happy_path_single_dep() -> None:
    m = _manifest({"@org/button": "^0.1"})
    graph = Resolver(_registry()).resolve(m)
    assert graph.target == "react"
    assert [r.spec_id for r in graph.resolutions] == ["@org/button"]
    # MVS strikt: kleinste Version ab Min (0.1.0) ist 0.1.0.
    assert graph.resolutions[0].version == Version(0, 1, 0)
    assert graph.resolutions[0].spec_sha256.startswith("sha256:")


def test_resolver_transitive_via_uses() -> None:
    # contact-form@0.1.0 hat uses: @org/button@^0.1
    m = _manifest({"@org/contact-form": "^0.1"})
    graph = Resolver(_registry()).resolve(m)
    ids = [r.spec_id for r in graph.resolutions]
    assert ids == sorted(ids)
    assert "@org/button" in ids
    assert "@org/contact-form" in ids


def test_resolver_diamond_picks_max_min() -> None:
    # onboarding-wizard fordert button@^0.1 (min 0.1.0)
    # login-screen fordert button@^0.1.1 (min 0.1.1)
    # MVS: max(min) = 0.1.1, kleinster Kandidat in beiden Ranges = 0.1.1
    m = _manifest(
        {
            "@org/onboarding-wizard": "^0.1",
            "@org/login-screen": "^0.1",
        }
    )
    graph = Resolver(_registry()).resolve(m)
    by_id = {r.spec_id: r for r in graph.resolutions}
    assert by_id["@org/button"].version == Version(0, 1, 1)
    assert by_id["@org/onboarding-wizard"].version == Version(0, 1, 0)
    assert by_id["@org/login-screen"].version == Version(0, 1, 0)


def test_resolver_resolutions_sorted_alphabetically() -> None:
    m = _manifest(
        {
            "@org/onboarding-wizard": "^0.1",
            "@org/button": "^0.1",
        }
    )
    graph = Resolver(_registry()).resolve(m)
    ids = [r.spec_id for r in graph.resolutions]
    assert ids == sorted(ids)


def test_resolver_missing_version_raises() -> None:
    # button hat 0.1.0 und 0.1.1 — fordere 0.2.x → keine Kandidaten.
    m = _manifest({"@org/button": "^0.2"})
    with pytest.raises(RangeConflictError):
        Resolver(_registry()).resolve(m)


def test_resolver_unknown_spec_raises() -> None:
    m = _manifest({"@org/does-not-exist": "^0.1"})
    with pytest.raises(VersionNotFoundError):
        Resolver(_registry()).resolve(m)


def test_resolver_incompatible_ranges() -> None:
    # exakt 0.1.0 vs. ^0.1.1 → keine Version erfüllt beide.
    m = _manifest(
        {
            "@org/button": "0.1.0",
            "@org/login-screen": "^0.1",  # zieht button@^0.1.1 ein
        }
    )
    with pytest.raises(RangeConflictError):
        Resolver(_registry()).resolve(m)


def test_resolver_invalid_range_in_manifest() -> None:
    m = _manifest({"@org/button": "~0.1"})
    with pytest.raises(ResolverError):
        Resolver(_registry()).resolve(m)
