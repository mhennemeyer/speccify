"""`resolve`-Tool: löst Manifest-Dependencies auf, ohne ein Lockfile zu schreiben.

Spiegelt die Resolver-Hälfte von `speccify lock` — Output ist der
`ResolvedGraph` als JSON-fähiges Dict mit Target und Resolutions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from speccify_core import LocalRegistry, ProjectManifest, Resolver

MANIFEST_FILENAME = "speccify.yaml"


@dataclass(frozen=True)
class ResolveResult:
    target: str
    resolutions: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {"target": self.target, "resolutions": list(self.resolutions)}


def run_resolve(
    project_root: Path,
    *,
    manifest_path: Path | None = None,
    registry_path: Path | None = None,
) -> ResolveResult:
    """Löst die Dependencies aus `speccify.yaml` auf.

    - `project_root`: Server-Startup-Projekt (Default-Manifest-Verzeichnis).
    - `manifest_path` (optional): explizites Manifest, sonst
      `<project_root>/speccify.yaml`.
    - `registry_path` (optional): überschreibt die Registry-Path-Auflösung
      aus dem Manifest.
    """
    manifest_file = manifest_path or (project_root / MANIFEST_FILENAME)
    if not manifest_file.is_file():
        raise FileNotFoundError(f"Kein Manifest gefunden: {manifest_file}")

    manifest = ProjectManifest.load(manifest_file)
    registry_dir = (
        registry_path.resolve() if registry_path is not None else manifest.resolved_registry_path()
    )
    registry = LocalRegistry(registry_dir)
    graph = Resolver(registry).resolve(manifest)

    resolutions = [
        {
            "spec_id": r.spec_id,
            "version": str(r.version),
            "spec_sha256": r.spec_sha256,
        }
        for r in graph.resolutions
    ]
    return ResolveResult(target=graph.target, resolutions=resolutions)
