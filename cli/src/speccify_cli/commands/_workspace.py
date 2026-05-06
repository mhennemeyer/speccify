"""Gemeinsamer Workspace-Kontext für die CLI-Subcommands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from speccify_core import LocalRegistry, ProjectManifest

MANIFEST_FILENAME = "speccify.yaml"
LOCKFILE_FILENAME = "speccify.lock"


@dataclass(frozen=True)
class WorkspaceContext:
    project_dir: Path
    manifest_path: Path
    lockfile_path: Path
    manifest: ProjectManifest
    registry: LocalRegistry

    @classmethod
    def load(
        cls,
        project_dir: Path,
        registry_override: Path | None = None,
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
        registry = LocalRegistry(registry_path)
        return cls(
            project_dir=project_dir,
            manifest_path=manifest_path,
            lockfile_path=project_dir / LOCKFILE_FILENAME,
            manifest=manifest,
            registry=registry,
        )
