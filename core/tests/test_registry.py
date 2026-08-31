"""Tests for bundles and the local playbook library."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import (
    LibraryError,
    MultiLibrary,
    Version,
    bundle_sha256,
)
from speccify_core.skill_library import LocalSkillLibrary

FIXTURES = Path("skills")


def test_bundle_carries_playbook_and_assets() -> None:
    bundle = LocalSkillLibrary(FIXTURES).fetch(
        "@speccify/macos-notarize-tauri", Version.parse("1.0.0")
    )
    assert set(bundle.files) == {
        "SKILL.md",
        "tools/verify-signatures/TOOL.md",
        "tools/verify-signatures/reference.sh",
    }
    assert bundle.asset_paths == (
        "tools/verify-signatures/TOOL.md",
        "tools/verify-signatures/reference.sh",
    )
    assert bundle.declared_id == "@speccify/macos-notarize-tauri"


def test_bundle_hash_covers_assets_and_paths() -> None:
    base = {"SKILL.md": b"a", "assets/x": b"b"}
    assert bundle_sha256(base) == bundle_sha256({"assets/x": b"b", "SKILL.md": b"a"})
    assert bundle_sha256(base) != bundle_sha256({"SKILL.md": b"a", "assets/y": b"b"})
    assert bundle_sha256(base) != bundle_sha256({"SKILL.md": b"a", "assets/x": b"c"})
    # Length prefixes keep neighbouring fields from bleeding into each other.
    assert bundle_sha256({"ab": b"c"}) != bundle_sha256({"a": b"bc"})


def test_list_playbooks_is_sorted_and_complete() -> None:
    found = LocalSkillLibrary(FIXTURES).list_playbooks()
    assert found == sorted(found)
    assert ("@speccify/apple-developer-id-cert", Version.parse("1.0.0")) in found


def test_unknown_version_names_what_is_available() -> None:
    with pytest.raises(LibraryError, match="Available: 1.0.0"):
        LocalSkillLibrary(FIXTURES).fetch("@speccify/macos-notarize-tauri", Version.parse("9.9.9"))


def test_a_bare_name_resolves_too() -> None:
    """`name` is the lookup key — host skill directories look up `<name>/`.

    The scope lives in the file, not in the path, so both forms find the same
    directory. Requiring a scope here would mean an agent could not ask for a
    skill by the only name it has seen.
    """
    library = LocalSkillLibrary(FIXTURES)
    assert library.list_versions("macos-notarize-tauri") == library.list_versions(
        "@speccify/macos-notarize-tauri"
    )


def test_library_root_must_exist(tmp_path: Path) -> None:
    with pytest.raises(LibraryError):
        LocalSkillLibrary(tmp_path / "missing")


def test_multi_library_routes_by_serves() -> None:
    local = LocalSkillLibrary(FIXTURES)

    class OnlyGit:
        via = "git"

        def serves(self, playbook_id: str) -> bool:
            return playbook_id.startswith("git+")

        def list_versions(self, playbook_id: str):
            return [Version.parse("2.0.0")]

        def fetch(self, playbook_id: str, version: Version):
            raise LibraryError("not reached in this test")

    multi = MultiLibrary([local, OnlyGit()])
    assert multi.serves("@speccify/macos-notarize-tauri")
    assert multi.serves("git+https://host/repo")
    assert multi.list_versions("git+https://host/repo") == [Version.parse("2.0.0")]
    assert multi.list_versions("@speccify/macos-notarize-tauri") == [Version.parse("1.0.0")]


def test_version_ordering_and_parsing() -> None:
    assert Version.parse("1.2.3") > Version.parse("1.2.2")
    with pytest.raises(ValueError):
        Version.parse("1.2")
