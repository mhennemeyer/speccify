"""Mock-Service: deterministische Mock-Closure aus der lokalen Registry (P2 Stage 5).

Dünner Adapter über `speccify_core.render_mock_closure` — Single Source of
Truth bleibt der Core; CLI (`speccify mock`), MCP-Tool `mock` und dieser
Service liefern byte-identische Dateien (Cross-Consistency-Vertrag).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from speccify_core import (
    MOCK_TEMPLATE_SET,
    MOCK_TEMPLATE_VERSION,
    LocalRegistry,
    mock_output_path,
    parse_composition,
    render_app_project,
    render_mock_closure,
    render_mock_files,
    resolve_composition_children,
)
from speccify_core.registry import Registry, Spec, Version


class UnknownMockTargetError(ValueError):
    """Angefragtes Mock-Target wird nicht unterstützt (P2: nur react)."""


@dataclass(frozen=True)
class MockServiceResult:
    spec_id: str
    version: str
    target: str
    files: dict[str, str]
    template_set: str
    template_version: str
    entry: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "version": self.version,
            "target": self.target,
            "files": self.files,
            "template_set": self.template_set,
            "template_version": self.template_version,
            "entry": self.entry,
        }


def mock_spec_from_registry(
    *,
    spec_id: str,
    version: str | None,
    target: str,
    registry_path: Path,
    registry: Registry | None = None,
) -> MockServiceResult:
    """Rendert die Mock-Closure für eine Registry-Spec (neueste Version bei `None`)."""
    if target != "react":
        raise UnknownMockTargetError(
            f"Mock-Target '{target}' wird nicht unterstützt (P2: nur 'react')."
        )
    registry = registry or LocalRegistry(registry_path)
    if version is None:
        versions = registry.list_versions(spec_id)
        if not versions:
            raise LookupError(f"Keine Versionen für {spec_id} in der Registry.")
        resolved_version = versions[-1]
    else:
        resolved_version = Version.parse(version)
    spec = registry.fetch(spec_id, resolved_version)
    result = render_mock_closure(spec, registry)
    return MockServiceResult(
        spec_id=spec_id,
        version=str(resolved_version),
        target=target,
        files={path: data.decode("utf-8") for path, data in result.files.items()},
        template_set=result.template_set,
        template_version=result.template_version,
        entry=mock_output_path(spec_id, kind=str(spec.parsed().get("kind", ""))),
    )


def mock_draft_spec_yaml(
    *,
    spec_yaml: str,
    target: str,
    registry_path: Path,
    registry: Registry | None = None,
) -> MockServiceResult:
    """Rendert die Mock-Closure für eine **ungespeicherte** Spec (Composer-Entwurf).

    Der Composer rendert seinen Canvas aus genau diesen Dateien — dem Output, den
    `speccify mock` nach dem Speichern erzeugen würde. Die Kinder kommen aus der
    Registry (nur der Entwurf selbst ist ungespeichert), deshalb ist das Ergebnis
    byte-identisch zur Registry-Variante, sobald der Entwurf gespeichert ist.
    """
    if target != "react":
        raise UnknownMockTargetError(
            f"Mock-Target '{target}' wird nicht unterstützt (P2: nur 'react')."
        )
    parsed = yaml.safe_load(spec_yaml)
    if not isinstance(parsed, dict):
        raise ValueError("Spec muss ein YAML-Mapping sein.")
    spec_id = str(parsed.get("id", ""))
    version_raw = str(parsed.get("version", ""))
    if not spec_id or not version_raw:
        raise ValueError("Entwurf braucht `id` und `version`, um gemockt zu werden.")

    raw_bytes = spec_yaml.encode("utf-8")
    draft = Spec(
        spec_id=spec_id,
        version=Version.parse(version_raw),
        raw_bytes=raw_bytes,
        path=Path("<draft>"),
    )
    registry = registry or LocalRegistry(registry_path)

    composition = parse_composition(parsed)
    children: dict[str, Spec] = {}
    if composition is not None:
        children = resolve_composition_children(composition, registry)

    files: dict[str, bytes] = {}
    for child in children.values():
        # Kinder kommen fertig aus der Registry — inkl. ihrer eigenen Closure.
        files.update(render_mock_closure(child, registry).files)
    files.update(render_mock_files(draft, children))

    return MockServiceResult(
        spec_id=spec_id,
        version=str(draft.version),
        target=target,
        files={path: data.decode("utf-8") for path, data in files.items()},
        template_set=MOCK_TEMPLATE_SET,
        template_version=MOCK_TEMPLATE_VERSION,
        entry=mock_output_path(spec_id, kind=str(parsed.get("kind", ""))),
    )


@dataclass(frozen=True)
class BuildServiceResult:
    """Ergebnis eines Projekt-Builds (`kind: app`, Phase P4)."""

    spec_id: str
    version: str
    target: str
    files: dict[str, str]
    template_set: str
    template_version: str
    mocks: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "version": self.version,
            "target": self.target,
            "files": self.files,
            "template_set": self.template_set,
            "template_version": self.template_version,
            "mocks": self.mocks,
        }


def build_app_from_registry(
    *,
    spec_id: str,
    version: str | None,
    target: str,
    registry_path: Path,
    registry: Registry | None = None,
) -> BuildServiceResult:
    """Baut das Projekt einer App-Spec aus der Registry (Web-Adapter, nur Mocks).

    Der Web-Pfad baut bewusst nur die Mock-Füllung: das Backend hat weder
    Replay-Cache-Flags noch LLM-Zugang im Vertrag. Implementierungs-Builds
    laufen über CLI/MCP (`--no-mocks`).
    """
    if target != "react":
        raise UnknownMockTargetError(
            f"Build-Target '{target}' wird nicht unterstützt (P4: nur 'react')."
        )
    registry = registry or LocalRegistry(registry_path)
    if version is None:
        versions = registry.list_versions(spec_id)
        if not versions:
            raise LookupError(f"Keine Versionen für {spec_id} in der Registry.")
        resolved_version = versions[-1]
    else:
        resolved_version = Version.parse(version)
    spec = registry.fetch(spec_id, resolved_version)
    result = render_app_project(spec, registry, mocks=True)
    return BuildServiceResult(
        spec_id=spec_id,
        version=str(resolved_version),
        target=target,
        files={path: data.decode("utf-8") for path, data in result.files.items()},
        template_set=result.template_set,
        template_version=result.template_version,
        mocks=result.mocks,
    )
