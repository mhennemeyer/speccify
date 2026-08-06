"""Tests for the project manifest."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from speccify_core import ManifestError, ProjectManifest


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "speccify.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_load_reads_dependencies_and_library(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        {
            "schema_version": 1,
            "library": {"path": "./my-playbooks"},
            "dependencies": {"@org/thing": "^1.0", "git+https://host/repo": "2.0.0"},
        },
    )
    manifest = ProjectManifest.load(path)
    assert manifest.dependencies == {"@org/thing": "^1.0", "git+https://host/repo": "2.0.0"}
    assert manifest.resolved_library_path() == (tmp_path / "my-playbooks").resolve()


def test_library_path_defaults_next_to_the_manifest(tmp_path: Path) -> None:
    manifest = ProjectManifest.load(_write(tmp_path, {"schema_version": 1}))
    assert manifest.resolved_library_path() == (tmp_path / "playbooks").resolve()


def test_round_trip_is_stable(tmp_path: Path) -> None:
    manifest = ProjectManifest.load(_write(tmp_path, {"schema_version": 1}))
    updated = manifest.with_dependency("@org/thing", "^1.0")
    updated.write()
    assert ProjectManifest.load(tmp_path / "speccify.yaml").dependencies == {"@org/thing": "^1.0"}


@pytest.mark.parametrize(
    "data",
    [
        pytest.param({"schema_version": 2}, id="wrong-version"),
        pytest.param({"schema_version": 1, "targets": ["react"]}, id="targets-are-gone"),
        pytest.param(
            {"schema_version": 1, "dependencies": {"no-scope": "^1.0"}}, id="unscoped-dependency"
        ),
        pytest.param({"schema_version": 1, "dependencies": {"@org/x": "latest"}}, id="bad-range"),
    ],
)
def test_broken_manifests_are_rejected(tmp_path: Path, data: dict) -> None:
    with pytest.raises(ManifestError):
        ProjectManifest.load(_write(tmp_path, data))
