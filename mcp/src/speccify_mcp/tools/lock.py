"""`lock`-Tool: löst Dependencies via MVS auf und schreibt `speccify.lock`.

Spiegelt `speccify lock` — Output ist ein Dict mit Target und resolved
Specs samt SHA-256. Schreibt das Lockfile auf Disk (Schreibtool).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from speccify_core import Resolver, build_lockfile

from ._workspace import WorkspaceContext


@dataclass(frozen=True)
class LockResult:
    target: str
    lockfile_path: str
    entries: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "lockfile_path": self.lockfile_path,
            "entries": list(self.entries),
        }


def run_lock(
    project_root: Path,
    *,
    registry_path: Path | None = None,
) -> LockResult:
    """Löst auf und schreibt `<project_root>/speccify.lock`."""
    ctx = WorkspaceContext.load(project_root, registry_override=registry_path)
    graph = Resolver(ctx.registry).resolve(ctx.manifest)
    lockfile = build_lockfile(target=graph.target, resolutions=list(graph.resolutions))
    lockfile.write(ctx.lockfile_path)

    entries = [
        {"spec_id": e.id, "version": e.version, "spec_sha256": e.sha256} for e in lockfile.entries
    ]
    return LockResult(
        target=lockfile.target,
        lockfile_path=str(ctx.lockfile_path),
        entries=entries,
    )
