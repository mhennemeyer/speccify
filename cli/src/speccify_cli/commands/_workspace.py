"""Gemeinsamer Workspace-Kontext für die CLI-Subcommands."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from speccify_core import (
    DEFAULT_GIT_CACHE_DIR,
    GitRegistry,
    LocalRegistry,
    ProjectManifest,
    Registry,
    RegistryError,
    Spec,
)

MANIFEST_FILENAME = "speccify.yaml"
LOCKFILE_FILENAME = "speccify.lock"

# Cache-Verzeichnis für Git-Quellen (Phase P5). Env-Override, damit Tests und
# CI ohne Zugriff auf `~/.cache` auskommen.
GIT_CACHE_ENV = "SPECCIFY_GIT_CACHE"


def git_cache_dir() -> Path:
    override = os.environ.get(GIT_CACHE_ENV)
    return Path(override) if override else DEFAULT_GIT_CACHE_DIR


def build_registries(
    registry_path: Path,
    *,
    offline: bool = False,
) -> list[Registry]:
    """Registry-Set der CLI: lokale Pseudo-Registry + Git-Quellen (Phase P5).

    Beide Registries beantworten nur die Ids, die sie bedienen können
    (`serves`) — die Reihenfolge ist damit egal und `@scope/name`-Projekte
    verhalten sich unverändert.
    """
    return [
        LocalRegistry(registry_path),
        GitRegistry(cache_dir=git_cache_dir(), offline=offline),
    ]


@dataclass(frozen=True)
class WorkspaceContext:
    project_dir: Path
    manifest_path: Path
    lockfile_path: Path
    manifest: ProjectManifest
    registry: LocalRegistry
    registries: list[Registry]

    @classmethod
    def load(
        cls,
        project_dir: Path,
        registry_override: Path | None = None,
        *,
        offline: bool = False,
    ) -> WorkspaceContext:
        manifest_path = project_dir / MANIFEST_FILENAME
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Kein {MANIFEST_FILENAME} in {project_dir} gefunden.")
        manifest = ProjectManifest.load(manifest_path)
        registry_path = (
            registry_override.resolve()
            if registry_override is not None
            else manifest.resolved_registry_path()
        )
        registries = build_registries(registry_path, offline=offline)
        return cls(
            project_dir=project_dir,
            manifest_path=manifest_path,
            lockfile_path=project_dir / LOCKFILE_FILENAME,
            manifest=manifest,
            registry=registries[0],  # type: ignore[arg-type]
            registries=registries,
        )


def fetch_spec(registries: list[Registry], spec_id: str, version) -> Spec:
    """Holt eine Spec aus der ersten Registry, die diese Id bedient."""
    last_error: RegistryError | None = None
    for registry in registries:
        serves = getattr(registry, "serves", None)
        if serves is not None and not serves(spec_id):
            continue
        try:
            return registry.fetch(spec_id, version)
        except RegistryError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RegistryError(f"Keine Registry im Set bedient '{spec_id}'.")


def list_versions(registries: list[Registry], spec_id: str) -> list:
    """Versionsliste aus der ersten Registry, die diese Id bedient."""
    for registry in registries:
        serves = getattr(registry, "serves", None)
        if serves is not None and not serves(spec_id):
            continue
        versions = registry.list_versions(spec_id)
        if versions:
            return versions
    return []
