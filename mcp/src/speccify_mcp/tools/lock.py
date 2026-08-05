"""`lock`-Tool: löst Dependencies via MVS auf und schreibt `speccify.lock`.

Spiegelt `speccify lock` — Output ist ein Dict mit Target und resolved
Specs samt SHA-256. Schreibt das Lockfile auf Disk (Schreibtool).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from speccify_core import Resolver, Workspace, build_lockfile
from speccify_core.manifest import ManifestError, ProjectManifest

from ._workspace import WorkspaceContext, build_registry


@dataclass(frozen=True)
class LockResult:
    target: str
    lockfile_path: str
    entries: list[dict[str, str]]
    # Phase 4: Im Workspace-Modus ist `target` evtl. mehrdeutig (Cross-Product
    # über Member-Targets). `targets` ist die kanonische Liste; `target` bleibt
    # für Abwärtskompatibilität auf das erste Target gesetzt.
    targets: tuple[str, ...] = ()
    workspace: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "targets": list(self.targets),
            "lockfile_path": self.lockfile_path,
            "entries": list(self.entries),
            "workspace": self.workspace,
        }


def _is_workspace_root(project_root: Path) -> bool:
    manifest_path = project_root / "speccify.yaml"
    if not manifest_path.is_file():
        return False
    try:
        return ProjectManifest.load(manifest_path).is_workspace_root
    except ManifestError:
        return False


def run_lock(
    project_root: Path,
    *,
    registry_path: Path | None = None,
    workspace_root: Path | None = None,
) -> LockResult:
    """Löst auf und schreibt `speccify.lock`.

    Phase 4: Optionales `workspace_root` schaltet auf den Workspace-Aggregat-Pfad
    (`Workspace.lock`) um. Ohne dieses Arg bleibt das Verhalten identisch zum
    Single-Project-Pfad — auch wenn `project_root` selbst ein Workspace-Root ist
    (für Abwärtskompatibilität älterer MCP-Clients). Detection erfolgt erst, wenn
    der Caller explizit `workspace_root` setzt.
    """
    target_root = workspace_root or project_root

    if workspace_root is not None and _is_workspace_root(target_root):
        workspace = Workspace.load(target_root)
        if registry_path is not None:
            reg_path = registry_path.resolve()
        else:
            reg_path = workspace.root_manifest.resolved_registry_path()
        lockfile = workspace.lock(build_registry(reg_path))
        lockfile_path = target_root / "speccify.lock"
        lockfile.write(lockfile_path)
        entries = [
            {
                "spec_id": e.id,
                "version": e.version,
                "spec_sha256": e.sha256,
                "target": e.target,
            }
            for e in lockfile.entries
        ]
        return LockResult(
            target=lockfile.targets[0] if lockfile.targets else "",
            targets=lockfile.targets,
            lockfile_path=str(lockfile_path),
            entries=entries,
            workspace=True,
        )

    # Single-Project-Pfad (unverändert).
    ctx = WorkspaceContext.load(project_root, registry_override=registry_path)
    graph = Resolver(ctx.registry).resolve(ctx.manifest)
    lockfile = build_lockfile(target=graph.target, resolutions=list(graph.resolutions))
    lockfile.write(ctx.lockfile_path)

    entries = [
        {"spec_id": e.id, "version": e.version, "spec_sha256": e.sha256} for e in lockfile.entries
    ]
    return LockResult(
        target=lockfile.target,
        targets=(lockfile.target,),
        lockfile_path=str(ctx.lockfile_path),
        entries=entries,
        workspace=False,
    )
