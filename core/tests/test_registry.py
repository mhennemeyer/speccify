"""Tests für `speccify_core.registry`."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core.registry import LocalRegistry, RegistryError, Version

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_ROOT = REPO_ROOT / "registry-fixtures"


def test_version_parse_and_order() -> None:
    assert Version.parse("0.1.0") == Version(0, 1, 0)
    assert Version.parse("1.2.3") == Version(1, 2, 3)
    assert Version(0, 1, 0) < Version(0, 1, 1) < Version(0, 2, 0) < Version(1, 0, 0)
    assert str(Version(1, 2, 3)) == "1.2.3"


@pytest.mark.parametrize("raw", ["0.1", "0.1.0-rc.1", "v0.1.0", "0.01.0", ""])
def test_version_parse_rejects_phase1a_disallowed(raw: str) -> None:
    with pytest.raises(ValueError):
        Version.parse(raw)


def test_list_versions_sorted_for_button() -> None:
    registry = LocalRegistry(REGISTRY_ROOT)
    versions = registry.list_versions("@org/button")
    assert versions == [Version(0, 1, 0), Version(0, 1, 1)]


def test_list_versions_unknown_spec_returns_empty() -> None:
    registry = LocalRegistry(REGISTRY_ROOT)
    assert registry.list_versions("@org/does-not-exist") == []


def test_fetch_returns_spec_with_bytes_and_version() -> None:
    registry = LocalRegistry(REGISTRY_ROOT)
    spec = registry.fetch("@org/button", Version(0, 1, 0))

    assert spec.spec_id == "@org/button"
    assert spec.version == Version(0, 1, 0)
    assert spec.path.name == "spec.speccify.yaml"
    # Originale Bytes (unverändert) für stabile Hashes:
    assert spec.raw_bytes == spec.path.read_bytes()
    parsed = spec.parsed()
    assert parsed["id"] == "@org/button"
    assert parsed["version"] == "0.1.0"


def test_fetch_missing_version_lists_available() -> None:
    registry = LocalRegistry(REGISTRY_ROOT)
    with pytest.raises(RegistryError, match="0.1.0|0.1.1"):
        registry.fetch("@org/button", Version(0, 9, 9))


def test_invalid_id_format_rejected() -> None:
    registry = LocalRegistry(REGISTRY_ROOT)
    with pytest.raises(RegistryError, match="@scope/name"):
        registry.list_versions("spec://button")


def test_registry_root_must_exist(tmp_path: Path) -> None:
    with pytest.raises(RegistryError):
        LocalRegistry(tmp_path / "missing")


def test_registry_root_must_be_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(RegistryError):
        LocalRegistry(file_path)


def test_all_phase0_specs_present() -> None:
    registry = LocalRegistry(REGISTRY_ROOT)
    for spec_id in (
        "@org/button",
        "@org/contact-form",
        "@org/http-api-client",
        "@org/onboarding-wizard",
        "@org/login-screen",
    ):
        assert registry.list_versions(spec_id), f"missing fixture: {spec_id}"
        registry.fetch(spec_id, Version(0, 1, 0))
