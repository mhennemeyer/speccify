"""Project manifest (`speccify.yaml`): which playbooks a project depends on.

Version 1 is a clean restart alongside the playbook schema — no targets (there
is no code generation), no workspaces (a playbook library is a flat directory).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

DEFAULT_MANIFEST_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "schema" / "manifest.schema.json"
)
DEFAULT_LIBRARY_PATH: str = "./skills"
MANIFEST_FILENAME = "speccify.yaml"
CURRENT_MANIFEST_SCHEMA_VERSION: int = 1


class ManifestError(Exception):
    """A manifest could not be read or validated."""


@dataclass(frozen=True)
class ProjectManifest:
    schema_version: int = CURRENT_MANIFEST_SCHEMA_VERSION
    dependencies: dict[str, str] = field(default_factory=dict)
    library_path: str = DEFAULT_LIBRARY_PATH
    source_path: Path | None = None

    @classmethod
    def load(cls, path: str | Path, schema_path: str | Path | None = None) -> ProjectManifest:
        manifest_path = Path(path)
        try:
            text = manifest_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ManifestError(f"Could not read manifest {manifest_path}: {exc}") from exc
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ManifestError(f"Invalid YAML in {manifest_path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ManifestError(f"A manifest must be a mapping: {manifest_path}")

        _validate(data, schema_path or DEFAULT_MANIFEST_SCHEMA_PATH, manifest_path)
        library = data.get("library") or {}
        return cls(
            schema_version=int(data["schema_version"]),
            dependencies={str(k): str(v) for k, v in (data.get("dependencies") or {}).items()},
            library_path=str(library.get("path", DEFAULT_LIBRARY_PATH)),
            source_path=manifest_path,
        )

    def resolved_library_path(self) -> Path:
        """Library directory, resolved relative to the manifest."""
        base = self.source_path.parent if self.source_path else Path.cwd()
        return (base / self.library_path).resolve()

    def with_dependency(self, playbook_id: str, range_raw: str) -> ProjectManifest:
        return ProjectManifest(
            schema_version=self.schema_version,
            dependencies={**self.dependencies, playbook_id: range_raw},
            library_path=self.library_path,
            source_path=self.source_path,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"schema_version": self.schema_version}
        if self.library_path != DEFAULT_LIBRARY_PATH:
            out["library"] = {"path": self.library_path}
        if self.dependencies:
            out["dependencies"] = dict(sorted(self.dependencies.items()))
        return out

    def write(self, path: str | Path | None = None) -> None:
        target = Path(path) if path is not None else self.source_path
        if target is None:
            raise ManifestError("No path to write the manifest to.")
        payload = self.to_dict()
        _validate(payload, DEFAULT_MANIFEST_SCHEMA_PATH, target)
        target.write_text(
            yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )


_VALIDATORS: dict[Path, Draft202012Validator] = {}


def _validate(data: Any, schema_path: str | Path, context: Path) -> None:
    key = Path(schema_path)
    validator = _VALIDATORS.get(key)
    if validator is None:
        try:
            schema = json.loads(key.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ManifestError(f"Could not read manifest schema {key}: {exc}") from exc
        validator = Draft202012Validator(schema)
        _VALIDATORS[key] = validator
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        location = "/".join(str(p) for p in first.absolute_path) or "$"
        raise ManifestError(
            f"{context}: manifest does not match the schema at {location}: {first.message}"
        )


__all__ = [
    "CURRENT_MANIFEST_SCHEMA_VERSION",
    "DEFAULT_LIBRARY_PATH",
    "DEFAULT_MANIFEST_SCHEMA_PATH",
    "MANIFEST_FILENAME",
    "ManifestError",
    "ProjectManifest",
]
