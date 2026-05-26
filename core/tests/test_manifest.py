"""Tests für `speccify_core.manifest`."""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core.manifest import (
    DEFAULT_REGISTRY_PATH,
    ManifestError,
    ProjectManifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_PROJECT = REPO_ROOT / "example-project"


def test_load_example_project_manifest() -> None:
    manifest = ProjectManifest.load(EXAMPLE_PROJECT / "speccify.yaml")

    # example-project/ wurde in Phase-3-Stage-1b-β auf Manifest-Schema v2 migriert.
    assert manifest.schema_version == 2
    assert manifest.targets == ("react",)
    assert manifest.target == "react"  # Backward-Compat-Property
    assert manifest.dependencies == {
        "@org/button": "^0.1",
        "@org/onboarding-wizard": "^0.1",
    }
    assert manifest.registry_path == "../registry-fixtures"
    assert manifest.resolved_registry_path() == (REPO_ROOT / "registry-fixtures").resolve()


def test_round_trip_preserves_fields(tmp_path: Path) -> None:
    src = ProjectManifest(
        schema_version=2,
        targets=("react",),
        dependencies={"@org/button": "^0.1", "@org/contact-form": "^0.1"},
        registry_path="./registry-fixtures",
    )
    out = tmp_path / "speccify.yaml"
    src.write(out)

    reloaded = ProjectManifest.load(out)
    assert reloaded.schema_version == src.schema_version
    assert reloaded.targets == src.targets
    assert reloaded.dependencies == src.dependencies
    assert reloaded.registry_path == src.registry_path


def test_default_registry_path_when_omitted(tmp_path: Path) -> None:
    manifest_path = tmp_path / "speccify.yaml"
    manifest_path.write_text(
        "schema_version: 1\ntarget: react\ndependencies: {}\n", encoding="utf-8"
    )

    manifest = ProjectManifest.load(manifest_path)
    assert manifest.registry_path == DEFAULT_REGISTRY_PATH


def test_missing_required_field_raises(tmp_path: Path) -> None:
    manifest_path = tmp_path / "speccify.yaml"
    manifest_path.write_text("schema_version: 1\ntarget: react\n", encoding="utf-8")

    with pytest.raises(ManifestError, match="dependencies"):
        ProjectManifest.load(manifest_path)


def test_invalid_dependency_range_raises(tmp_path: Path) -> None:
    manifest_path = tmp_path / "speccify.yaml"
    manifest_path.write_text(
        'schema_version: 1\ntarget: react\ndependencies:\n  "@org/button": "~0.1"\n',
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="dependencies"):
        ProjectManifest.load(manifest_path)


def test_invalid_dependency_id_pattern_raises(tmp_path: Path) -> None:
    manifest_path = tmp_path / "speccify.yaml"
    manifest_path.write_text(
        'schema_version: 1\ntarget: react\ndependencies:\n  "BadId": "^0.1"\n',
        encoding="utf-8",
    )

    with pytest.raises(ManifestError):
        ProjectManifest.load(manifest_path)


def test_unknown_top_level_field_rejected(tmp_path: Path) -> None:
    manifest_path = tmp_path / "speccify.yaml"
    manifest_path.write_text(
        "schema_version: 1\ntarget: react\ndependencies: {}\nextra: nope\n",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError):
        ProjectManifest.load(manifest_path)


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="nicht lesen"):
        ProjectManifest.load(tmp_path / "does-not-exist.yaml")
