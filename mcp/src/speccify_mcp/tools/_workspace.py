"""Gemeinsame Workspace-/Cache-Helper für MCP-Tools.

Eigenständige Variante des CLI-`WorkspaceContext` (keine
`speccify-cli`-Abhängigkeit). Spiegelt die Konventionen aus
`cli/commands/_workspace.py` + `cli/commands/_llm_client.py` 1:1.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from speccify_core import (
    LocalRegistry,
    ProjectManifest,
    ReplayCache,
    ReplayCacheClient,
)

MANIFEST_FILENAME = "speccify.yaml"
LOCKFILE_FILENAME = "speccify.lock"
CACHE_DIR_ENV = "SPECCIFY_CACHE_DIR"

# Repo-lokaler Default-Cache (gleiche Konvention wie cli/_llm_client.py).
# mcp/src/speccify_mcp/tools/_workspace.py → parents[4] == Repo-Root.
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CACHE_DIR: Path = _REPO_ROOT / "tests" / "fixtures" / "llm-cache"


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


def resolve_cache_dir(override: Path | None) -> Path:
    if override is not None:
        return override.resolve()
    env = os.environ.get(CACHE_DIR_ENV)
    if env:
        return Path(env).resolve()
    return DEFAULT_CACHE_DIR


def build_replay_client(
    *, offline: bool = True, cache_dir: Path | None = None
) -> ReplayCacheClient:
    cache = ReplayCache(resolve_cache_dir(cache_dir))
    return ReplayCacheClient(cache, offline=offline)
