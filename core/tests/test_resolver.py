"""Tests for the playbook resolver (MVS over local sources)."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import (
    LocalLibrary,
    ProjectManifest,
    Range,
    RangeConflictError,
    Resolver,
    Version,
    VersionNotFoundError,
    build_lockfile,
    parse_uses_entry,
)

FIXTURES = Path("playbooks")


def _manifest(**dependencies: str) -> ProjectManifest:
    return ProjectManifest(dependencies=dict(dependencies))


def test_range_parsing_and_containment() -> None:
    caret = Range.parse("^1.2")
    assert caret.contains(Version.parse("1.9.0"))
    assert not caret.contains(Version.parse("2.0.0"))
    zero = Range.parse("^0.1")
    assert zero.contains(Version.parse("0.1.7"))
    assert not zero.contains(Version.parse("0.2.0"))
    exact = Range.parse("1.0.0")
    assert exact.contains(Version.parse("1.0.0"))
    assert not exact.contains(Version.parse("1.0.1"))


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ("@org/x@^1.0", ("@org/x", "^1.0")),
        ("@org/x", ("@org/x", "^0.0")),
        ("git+https://host/repo@^1.2", ("git+https://host/repo", "^1.2")),
        ("git+https://host/repo#play/a@2.0.0", ("git+https://host/repo#play/a", "2.0.0")),
        ("git+https://host/repo", ("git+https://host/repo", "^0.0")),
    ],
)
def test_parse_uses_entry(entry: str, expected: tuple[str, str]) -> None:
    assert parse_uses_entry(entry) == expected


def test_resolve_follows_child_playbooks() -> None:
    graph = Resolver(LocalLibrary(FIXTURES)).resolve(
        _manifest(**{"@speccify/macos-notarize-tauri": "^1.0"})
    )
    resolved = {r.playbook_id: r for r in graph.resolutions}
    # The child comes along because a step delegates to it.
    assert set(resolved) == {
        "@speccify/macos-notarize-tauri",
        "@speccify/apple-developer-id-cert",
    }
    assert resolved["@speccify/apple-developer-id-cert"].version == Version.parse("1.0.0")
    assert resolved["@speccify/macos-notarize-tauri"].bundle_sha256.startswith("sha256:")
    assert resolved["@speccify/macos-notarize-tauri"].via == "local"


def test_unknown_playbook_reports_who_asked() -> None:
    with pytest.raises(VersionNotFoundError, match="<root>"):
        Resolver(LocalLibrary(FIXTURES)).resolve(_manifest(**{"@org/nope": "^1.0"}))


def test_conflicting_ranges_fail_loudly() -> None:
    resolver = Resolver(LocalLibrary(FIXTURES))
    with pytest.raises(RangeConflictError, match="available: 1.0.0"):
        resolver.resolve_constraints(
            {
                "@speccify/apple-developer-id-cert": [
                    ("^1.0", "<root>"),
                    ("^2.0", "@other/playbook@1.0.0"),
                ]
            }
        )


def test_lockfile_round_trip(tmp_path: Path) -> None:
    graph = Resolver(LocalLibrary(FIXTURES)).resolve(
        _manifest(**{"@speccify/macos-notarize-tauri": "^1.0"})
    )
    lockfile = build_lockfile(list(graph.resolutions))
    path = tmp_path / "speccify.lock"
    lockfile.write(path)

    from speccify_core import Lockfile

    loaded = Lockfile.load(path)
    assert loaded.schema_version == 1
    assert [e.id for e in loaded.entries] == sorted(e.id for e in loaded.entries)
    entry = loaded.entry("@speccify/macos-notarize-tauri")
    assert entry.resolved_via == "local"
    assert entry.bundle_sha256.startswith("sha256:")
    # Local sources have no commit to pin.
    assert entry.source_commit is None
