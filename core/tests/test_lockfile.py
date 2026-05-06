"""Lockfile-Tests: Round-Trip, Schema-Fehler, sortierte Reihenfolge, build_lockfile."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import (
    GeneratedFile,
    GeneratorPin,
    LocalRegistry,
    LockEntry,
    Lockfile,
    LockfileError,
    ProjectManifest,
    Resolver,
    build_lockfile,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "registry-fixtures"

_HASH_A = "sha256:" + "a" * 64
_HASH_B = "sha256:" + "b" * 64
_HASH_C = "sha256:" + "c" * 64


def _entry(spec_id: str, sha: str, files: tuple[GeneratedFile, ...] = ()) -> LockEntry:
    return LockEntry(
        id=spec_id,
        version="0.1.0",
        sha256=sha,
        resolved_via="registry-fixtures",
        target="react",
        generator=GeneratorPin(),
        generated_files_sha256=files,
    )


def test_lockfile_round_trip(tmp_path: Path) -> None:
    lock = Lockfile(
        target="react",
        entries=(
            _entry("@org/button", _HASH_A),
            _entry("@org/contact-form", _HASH_B),
        ),
    )
    out = tmp_path / "speccify.lock"
    lock.write(out)
    loaded = Lockfile.load(out)
    assert loaded == lock


def test_lockfile_writes_alphabetically(tmp_path: Path) -> None:
    lock = Lockfile(
        target="react",
        entries=(
            _entry("@org/contact-form", _HASH_B),
            _entry("@org/button", _HASH_A),
        ),
    )
    out = tmp_path / "speccify.lock"
    lock.write(out)
    text = out.read_text(encoding="utf-8")
    assert text.index("@org/button") < text.index("@org/contact-form")


def test_lockfile_schema_violation_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "speccify.lock"
    bad.write_text(
        "schema_version: 1\n"
        "target: react\n"
        "specs:\n"
        "  - id: 'NOT-AN-ID'\n"
        "    version: '0.1.0'\n"
        "    sha256: '" + _HASH_A + "'\n"
        "    resolved_via: registry-fixtures\n"
        "    target: react\n"
        "    generator: {kind: template, template_set: phase-1a-stub, template_version: 0.1.0}\n"
        "    generated_files_sha256: []\n",
        encoding="utf-8",
    )
    with pytest.raises(LockfileError):
        Lockfile.load(bad)


def test_lockfile_with_generated_files_replaces_only_target(tmp_path: Path) -> None:
    lock = Lockfile(
        target="react",
        entries=(
            _entry("@org/button", _HASH_A),
            _entry("@org/contact-form", _HASH_B),
        ),
    )
    updated = lock.with_generated_files(
        "@org/button",
        [GeneratedFile(path="out/org/button.md", sha256=_HASH_C)],
    )
    by_id = {e.id: e for e in updated.entries}
    assert by_id["@org/button"].generated_files_sha256[0].sha256 == _HASH_C
    assert by_id["@org/contact-form"].generated_files_sha256 == ()


def test_lockfile_with_generated_files_unknown_id() -> None:
    lock = Lockfile(target="react", entries=(_entry("@org/button", _HASH_A),))
    with pytest.raises(LockfileError):
        lock.with_generated_files("@org/missing", [])


def test_build_lockfile_from_resolver_graph(tmp_path: Path) -> None:
    manifest = ProjectManifest(
        schema_version=1,
        target="react",
        dependencies={"@org/contact-form": "^0.1"},
        registry_path=str(FIXTURES),
        source_path=None,
    )
    graph = Resolver(LocalRegistry(FIXTURES)).resolve(manifest)
    lock = build_lockfile(target=graph.target, resolutions=list(graph.resolutions))

    ids = [e.id for e in lock.entries]
    assert ids == sorted(ids)
    assert all(e.target == "react" for e in lock.entries)
    assert all(e.generator.template_set == "phase-1a-stub" for e in lock.entries)
    assert all(e.generated_files_sha256 == () for e in lock.entries)
    assert all(e.sha256.startswith("sha256:") for e in lock.entries)

    # Round-trip mit Schema-Validation
    out = tmp_path / "speccify.lock"
    lock.write(out)
    assert Lockfile.load(out) == lock
