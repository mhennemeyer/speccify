"""Projekt-Manifest (`speccify.yaml`) — Loader, Schema-Validation und deterministischer Writer."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema import exceptions as js_exceptions

# core/src/speccify_core/manifest.py → ../../../schema/manifest.schema.json
DEFAULT_MANIFEST_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "schema" / "manifest.schema.json"
)

DEFAULT_REGISTRY_PATH: str = "./registry-fixtures"


class ManifestError(Exception):
    """Manifest konnte nicht geladen oder nicht validiert werden."""


CURRENT_MANIFEST_SCHEMA_VERSION: int = 2


@dataclass(frozen=True)
class ProjectManifest:
    """Immutables Projekt-Manifest. Pfade werden relativ zum Manifest aufgelöst.

    Phase-3-Stage-1b-β: `targets: tuple[str, ...]` ist Single-Source-of-Truth (≥ 1 Eintrag).
    `target` bleibt als Backward-Compat-Property (erstes Element der Liste).
    """

    schema_version: int
    targets: tuple[str, ...] = ()
    dependencies: dict[str, str] = field(default_factory=dict)
    registry_path: str = DEFAULT_REGISTRY_PATH
    source_path: Path | None = None
    workspaces: tuple[str, ...] = ()

    @property
    def is_workspace_root(self) -> bool:
        """True, wenn dieses Manifest mindestens ein `workspaces:`-Glob enthält."""
        return bool(self.workspaces)

    @property
    def target(self) -> str:
        """Backward-Compat: liefert das erste Target. Erwartet single-target-Manifest."""
        if len(self.targets) != 1:
            raise ManifestError(
                f"Manifest hat {len(self.targets)} Targets, `.target` ist nur für "
                f"single-target-Manifeste definiert. Nutze `.targets`."
            )
        return self.targets[0]

    @classmethod
    def load(
        cls,
        path: str | Path,
        schema_path: str | Path | None = None,
    ) -> ProjectManifest:
        manifest_path = Path(path)
        try:
            text = manifest_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ManifestError(f"Konnte Manifest nicht lesen: {manifest_path}: {exc}") from exc

        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ManifestError(f"Ungültiges YAML in {manifest_path}: {exc}") from exc

        if not isinstance(data, dict):
            raise ManifestError(
                f"Manifest muss ein YAML-Mapping sein, ist aber {type(data).__name__}: "
                f"{manifest_path}"
            )

        # v1 → v2 Migration: `target: str` → `targets: [target]`, schema_version 1 → 2.
        data = _migrate_manifest_to_v2(data)

        _validate_against_schema(data, schema_path or DEFAULT_MANIFEST_SCHEMA_PATH, manifest_path)

        registry_block = data.get("registry") or {}
        registry_path = registry_block.get("path", DEFAULT_REGISTRY_PATH)
        targets_raw = data.get("targets", []) or []
        workspaces_raw = data.get("workspaces", []) or []
        return cls(
            schema_version=data["schema_version"],
            targets=tuple(targets_raw),
            dependencies=dict(data.get("dependencies", {})),
            registry_path=registry_path,
            source_path=manifest_path,
            workspaces=tuple(workspaces_raw),
        )

    def write(self, path: str | Path) -> None:
        """Schreibt das Manifest deterministisch (sortierte Keys, stable Layout)."""
        out_path = Path(path)
        payload: dict[str, Any] = {"schema_version": self.schema_version}
        if self.targets:
            payload["targets"] = list(self.targets)
        if self.workspaces:
            payload["workspaces"] = list(self.workspaces)
        payload["registry"] = {"path": self.registry_path}
        payload["dependencies"] = dict(sorted(self.dependencies.items()))
        text = yaml.safe_dump(
            payload,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )
        out_path.write_text(text, encoding="utf-8")

    def resolved_registry_path(self) -> Path:
        """Löst `registry_path` relativ zum Manifest-Verzeichnis auf."""
        registry = Path(self.registry_path)
        if registry.is_absolute() or self.source_path is None:
            return registry
        return (self.source_path.parent / registry).resolve()


def _migrate_manifest_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """In-Memory-Migration eines v1-Manifest-Dicts auf v2.

    v1: `{schema_version: 1, target: str, ...}` → v2: `{schema_version: 2, targets: [target], ...}`.
    Andere Schema-Versionen werden unverändert zurückgegeben (Schema-Validator meldet den Fehler).
    """
    if data.get("schema_version") == 1 and "target" in data and "targets" not in data:
        migrated = dict(data)
        migrated["schema_version"] = 2
        migrated["targets"] = [migrated.pop("target")]
        return migrated
    return data


def _validate_against_schema(data: Any, schema_path: str | Path, source: Path) -> None:
    schema_p = Path(schema_path)
    with schema_p.open("r", encoding="utf-8") as fh:
        schema: dict[str, Any] = json.load(fh)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        formatted = "; ".join(_format_error(err) for err in errors)
        raise ManifestError(f"Manifest entspricht nicht dem Schema ({source}): {formatted}")


def _format_error(error: js_exceptions.ValidationError) -> str:
    if not error.absolute_path:
        return error.message
    parts: list[str] = []
    for part in error.absolute_path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            parts.append(f".{part}")
    pointer = "$" + "".join(parts)
    return f"{pointer}: {error.message}"
