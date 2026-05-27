"""`pull`-Tool: rendert Specs aus dem Lockfile und schreibt Output-Dateien.

Spiegelt `speccify pull` 1:1. Schreibt gerenderte Dateien atomar nach
`out_dir`, aktualisiert `generated_files_sha256` + `LlmGeneratorPin` im
Lockfile. Offline-Default (Cache-Miss → Fehler).
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from speccify_core import (
    GeneratedFile,
    LlmGeneratorPin,
    Lockfile,
    LockfileError,
    Version,
    render_for_target,
)
from speccify_core.codegen import react_llm
from speccify_core.manifest import ManifestError, ProjectManifest

from ._workspace import WorkspaceContext, build_replay_client


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".speccify-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


@dataclass(frozen=True)
class PullResult:
    target: str
    out_dir: str
    lockfile_path: str
    files_written: list[str]
    workspace: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "out_dir": self.out_dir,
            "lockfile_path": self.lockfile_path,
            "files_written": list(self.files_written),
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


def run_pull(
    project_root: Path,
    out_dir: Path,
    *,
    target: str | None = None,
    registry_path: Path | None = None,
    offline: bool = True,
    cache_dir: Path | None = None,
    workspace_root: Path | None = None,
) -> PullResult:
    """Rendert alle Lockfile-Einträge nach `out_dir` und aktualisiert das Lockfile.

    Phase 4: Optionales `workspace_root` delegiert an `speccify pull` im Workspace-
    Modus (siehe `cli.commands.pull.run_pull`); Outputs landen pro Member unter
    `<member>/speccify_generated/<target>/`, `out_dir` wird ignoriert.
    """
    if workspace_root is not None:
        # Late-Import wegen Phase-4-Workspace-Bridge: MCP delegiert an die CLI-
        # Implementierung, die Workspace-aware ist (Single-Source-of-Truth).
        from speccify_cli.commands.pull import run_pull as cli_run_pull

        if target is not None:
            raise LockfileError(
                "`target` ist im Workspace-Modus nicht unterstützt — jedes Member "
                "deklariert seine eigenen Targets."
            )
        ws_lockfile = cli_run_pull(
            workspace_root,
            out_dir=out_dir,  # wird vom workspace-pfad ignoriert
            registry_override=registry_path,
            offline=offline,
            cache_dir=cache_dir,
        )
        files_written = sorted(
            {f.path for e in ws_lockfile.entries for f in e.generated_files_sha256}
        )
        return PullResult(
            target=",".join(ws_lockfile.targets),
            out_dir=str(workspace_root.resolve()),
            lockfile_path=str(workspace_root / "speccify.lock"),
            files_written=files_written,
            workspace=True,
        )

    ctx = WorkspaceContext.load(project_root, registry_override=registry_path)
    if not ctx.lockfile_path.is_file():
        raise LockfileError(f"Kein Lockfile in {project_root}. Bitte zuerst `lock` aufrufen.")
    lockfile = Lockfile.load(ctx.lockfile_path)

    if target is not None and target != lockfile.target:
        raise LockfileError(
            f"target '{target}' weicht vom Lockfile-Target "
            f"'{lockfile.target}' ab. Bitte zuerst `lock` mit gewünschtem "
            f"Target ausführen."
        )
    effective_target = lockfile.target

    llm_client = build_replay_client(offline=offline, cache_dir=cache_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    files_written: list[str] = []
    updated = lockfile
    for entry in lockfile.entries:
        spec = ctx.registry.fetch(entry.id, Version.parse(entry.version))
        rendered = render_for_target(spec, effective_target, llm_client=llm_client)
        generated: list[GeneratedFile] = []
        for rel_path, data in sorted(rendered.files.items()):
            abs_path = out_dir / rel_path
            _atomic_write(abs_path, data)
            digest = hashlib.sha256(data).hexdigest()
            generated.append(GeneratedFile(path=rel_path, sha256=f"sha256:{digest}"))
            files_written.append(rel_path)
        updated = updated.with_generated_files(entry.id, generated)
        if rendered.cache_key is not None:
            pin = LlmGeneratorPin(
                provider=react_llm.PROVIDER,
                model=rendered.cache_key.model,
                prompt_version=rendered.cache_key.prompt_version,
                cache_key=f"sha256:{rendered.cache_key.digest()}",
                seed=rendered.cache_key.seed,
            )
            updated = updated.with_generator(entry.id, pin)

    updated.write(ctx.lockfile_path)
    return PullResult(
        target=effective_target,
        out_dir=str(out_dir.resolve()),
        lockfile_path=str(ctx.lockfile_path),
        files_written=sorted(files_written),
    )
