"""Composer-Services (P3): Spec-Detail, Validierung und Speichern.

Der visuelle Composer ist ein Spec-Editor — sein Zustand ist die YAML-Datei
in der lokalen Registry. Diese Services sind die agent-bedienbare Grundlage:
alles, was die Composer-UI kann, geht auch über diese Funktionen bzw. die
HTTP-Routen darüber (`routes/composer.py`).

Serialisierung: Der `api:`-Block wird als JSON-Contract ausgeliefert (inkl.
`kind`/`enumValues` pro Typ), damit die UI typisierte Editoren und
Verdrahtungs-Dropdowns bauen kann, ohne Typ-Ausdrücke selbst zu parsen.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from speccify_core import (
    CompositionResolutionError,
    LocalRegistry,
    SchemaValidator,
    component_api,
    parse_composition,
    resolve_composition_children,
    validate_composition,
)
from speccify_core.api import ComponentApi, TypeRef
from speccify_core.registry import Version

_SPEC_FILENAME = "spec.speccify.yaml"


class SpecValidationFailed(ValueError):
    """Spec ist nicht speicherbar; `issues` trägt die strukturierte Befundliste."""

    def __init__(self, issues: list[dict[str, str]]) -> None:
        super().__init__(f"{len(issues)} Validierungs-Problem(e).")
        self.issues = issues


# --- Serialisierung -----------------------------------------------------------


def _type_dict(type_ref: TypeRef) -> dict[str, Any]:
    return {
        "raw": type_ref.raw,
        "kind": type_ref.kind,
        "enumValues": list(type_ref.enum_values),
    }


def api_contract_dict(api: ComponentApi) -> dict[str, Any]:
    """JSON-Contract des `api:`-Blocks für die Composer-UI."""
    return {
        "props": [
            {
                "name": p.name,
                "type": _type_dict(p.type),
                "required": p.required,
                "default": p.default,
                "hasDefault": p.has_default,
                "description": p.description,
                "constraints": list(p.constraints),
                "mapTo": f"{p.map_to[0]}.{p.map_to[1]}" if p.map_to else None,
            }
            for p in api.props
        ],
        "events": [
            {
                "name": e.name,
                "payload": [
                    {"name": field_name, "type": _type_dict(ref)} for field_name, ref in e.payload
                ],
                "description": e.description,
            }
            for e in api.events
        ],
        "slots": [
            {"name": s.name, "optional": s.optional, "description": s.description}
            for s in api.slots
        ],
        "fixtures": [
            {"name": f.name, "data": f.data, "description": f.description} for f in api.fixtures
        ],
        "outputs": [{"name": o.name, "type": _type_dict(o.type)} for o in api.outputs],
    }


# --- Spec-Detail --------------------------------------------------------------


def spec_detail(
    *,
    registry_path: Path,
    spec_id: str,
    version: str | None = None,
) -> dict[str, Any]:
    """Detail einer Registry-Spec: YAML, Contract-JSON, Komposition, Kind-Contracts."""
    registry = LocalRegistry(registry_path)
    versions = registry.list_versions(spec_id)
    if not versions:
        raise LookupError(f"Keine Versionen für {spec_id} in der Registry.")
    resolved_version = Version.parse(version) if version else versions[-1]
    spec = registry.fetch(spec_id, resolved_version)
    parsed = spec.parsed()
    composition = parse_composition(parsed)

    children: dict[str, Any] = {}
    if composition is not None:
        resolved = resolve_composition_children(composition, registry)
        children = {
            alias: {
                "id": child.spec_id,
                "version": str(child.version),
                "kind": str(child.parsed().get("kind", "")),
                "title": str(child.parsed().get("title", child.spec_id)),
                "api": api_contract_dict(component_api(child.parsed())),
            }
            for alias, child in resolved.items()
        }

    return {
        "id": spec_id,
        "version": str(resolved_version),
        "versions": [str(v) for v in versions],
        "kind": str(parsed.get("kind", "")),
        "title": str(parsed.get("title", spec_id)),
        "summary": str(parsed.get("summary", "")).strip(),
        "yaml": spec.raw_bytes.decode("utf-8"),
        "api": api_contract_dict(component_api(parsed)),
        "composition": parsed.get("composition"),
        "children": children,
    }


# --- Validierung + Speichern --------------------------------------------------


@dataclass(frozen=True)
class ValidationOutcome:
    ok: bool
    issues: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "issues": self.issues}


def validate_spec_yaml(yaml_bytes: bytes, *, registry_path: Path) -> ValidationOutcome:
    """Volle Validierung: YAML-Parse → Schema v1 → Kompositions-Typprüfung.

    Kompositions-Kinder werden gegen die Registry aufgelöst; Auflösungsfehler
    sind Issues (Quelle `composition`), keine Exceptions — die UI zeigt sie an.
    """
    issues: list[dict[str, str]] = []
    try:
        parsed = yaml.safe_load(yaml_bytes.decode("utf-8"))
    except yaml.YAMLError as exc:
        return ValidationOutcome(
            ok=False,
            issues=[{"path": "$", "message": f"YAML-Parse-Fehler: {exc}", "source": "yaml"}],
        )
    if not isinstance(parsed, dict):
        return ValidationOutcome(
            ok=False,
            issues=[{"path": "$", "message": "Spec muss ein Mapping sein.", "source": "yaml"}],
        )

    validator = SchemaValidator()
    for issue in validator.iter_issues(parsed):
        issues.append({"path": issue.path, "message": issue.message, "source": "schema"})

    composition = None
    if not issues:
        try:
            composition = parse_composition(parsed)
        except ValueError as exc:
            issues.append({"path": "$.composition", "message": str(exc), "source": "composition"})

    if composition is not None:
        try:
            registry = LocalRegistry(registry_path)
            children = resolve_composition_children(composition, registry)
        except CompositionResolutionError as exc:
            issues.append(
                {"path": "$.composition.uses", "message": str(exc), "source": "composition"}
            )
        else:
            child_apis = {alias: component_api(child.parsed()) for alias, child in children.items()}
            for comp_issue in validate_composition(parsed, child_apis):
                issues.append(
                    {
                        "path": comp_issue.path,
                        "message": comp_issue.message,
                        "source": "composition",
                    }
                )

    return ValidationOutcome(ok=not issues, issues=issues)


def save_spec_yaml(yaml_bytes: bytes, *, registry_path: Path) -> dict[str, Any]:
    """Validiert und schreibt eine Spec in die Registry (Pfad aus id + version).

    Nur scoped IDs (`@scope/name`) sind speicherbar — das Registry-Layout
    braucht den Scope. Überschreiben einer existierenden Version ist im
    Composer-Kontext erlaubt (lokales Dev-Tool, Git ist die Historie).
    """
    outcome = validate_spec_yaml(yaml_bytes, registry_path=registry_path)
    if not outcome.ok:
        raise SpecValidationFailed(outcome.issues)

    parsed = yaml.safe_load(yaml_bytes.decode("utf-8"))
    spec_id = str(parsed["id"])
    version = str(parsed["version"])
    if not spec_id.startswith("@") or "/" not in spec_id:
        raise SpecValidationFailed(
            [
                {
                    "path": "$.id",
                    "message": f"Nur scoped IDs (@scope/name) sind speicherbar, nicht '{spec_id}'.",
                    "source": "save",
                }
            ]
        )
    scope, name = spec_id[1:].split("/", 1)
    target = registry_path / scope / name / version / _SPEC_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(yaml_bytes)
    return {"id": spec_id, "version": version, "path": str(target)}
