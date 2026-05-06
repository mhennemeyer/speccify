"""`speccify pull`: rendert Specs aus dem Lockfile und schreibt Output-Hashes zurück.

Phase 1a:
- Liest das Lockfile (das `lock` zuvor erzeugt hat); ohne Lockfile → klarer Fehler.
- Holt jede Spec mit `(id, version)` aus der `LocalRegistry`, ruft den Stub-Codegen.
- Schreibt jede Output-Datei atomar (tmp-File + `os.replace`) nach `--out`.
- Aktualisiert `generated_files_sha256` im Lockfile pro Eintrag und speichert es zurück.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import typer
from speccify_core import (
    GeneratedFile,
    Lockfile,
    LockfileError,
)
from speccify_core.codegen import render_to_files
from speccify_core.manifest import ManifestError
from speccify_core.registry import RegistryError, Version

from speccify_cli.commands._workspace import WorkspaceContext


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


def run_pull(
    project_dir: Path,
    out_dir: Path,
    target_override: str | None = None,
    registry_override: Path | None = None,
) -> Lockfile:
    ctx = WorkspaceContext.load(project_dir, registry_override=registry_override)
    if not ctx.lockfile_path.is_file():
        raise LockfileError(
            f"Kein Lockfile in {project_dir} gefunden. Bitte zuerst `speccify lock` ausführen."
        )
    lockfile = Lockfile.load(ctx.lockfile_path)

    target = target_override or lockfile.target
    if target_override is not None and target_override != lockfile.target:
        raise LockfileError(
            f"--target '{target_override}' weicht vom Lockfile-Target '{lockfile.target}' ab. "
            f"Bitte zuerst `speccify lock` mit gewünschtem Target ausführen."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    updated = lockfile
    for entry in lockfile.entries:
        spec = ctx.registry.fetch(entry.id, Version.parse(entry.version))
        files = render_to_files(spec, target)
        generated: list[GeneratedFile] = []
        for rel_path, data in sorted(files.items()):
            abs_path = out_dir / rel_path
            _atomic_write(abs_path, data)
            digest = hashlib.sha256(data).hexdigest()
            generated.append(GeneratedFile(path=rel_path, sha256=f"sha256:{digest}"))
        updated = updated.with_generated_files(entry.id, generated)

    updated.write(ctx.lockfile_path)
    return updated


def pull_command(
    project_dir: Path | None = typer.Option(  # noqa: B008
        None,
        "--project",
        "-p",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Projekt-Verzeichnis mit speccify.yaml/speccify.lock (Default: aktuelles Verz.).",
    ),
    out: Path = typer.Option(  # noqa: B008
        Path("./out"),
        "--out",
        file_okay=False,
        dir_okay=True,
        help="Ausgabeverzeichnis für gerenderte Dateien.",
    ),
    target: str | None = typer.Option(  # noqa: B008
        None,
        "--target",
        help="Codegen-Target (Default: Target aus Lockfile).",
    ),
    registry: Path | None = typer.Option(  # noqa: B008
        None,
        "--registry",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Optionale Registry-Pfad-Überschreibung.",
    ),
) -> None:
    """Rendert resolved Specs aus dem Lockfile und aktualisiert Output-Hashes."""
    project = project_dir or Path.cwd()
    try:
        lockfile = run_pull(
            project,
            out_dir=out,
            target_override=target,
            registry_override=registry,
        )
    except (ManifestError, RegistryError, LockfileError, FileNotFoundError) as exc:
        typer.echo(f"✗ speccify pull fehlgeschlagen: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    files_total = sum(len(e.generated_files_sha256) for e in lockfile.entries)
    typer.echo(
        f"✓ {files_total} Dateien gerendert ({len(lockfile.entries)} Specs) → {out.resolve()}"
    )
