"""`speccify lock`: löst Manifest-Dependencies auf und schreibt `speccify.lock`."""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core import (
    Lockfile,
    Resolver,
    ResolverError,
    build_lockfile,
)
from speccify_core.manifest import ManifestError
from speccify_core.registry import RegistryError

from speccify_cli.commands._workspace import WorkspaceContext


def run_lock(project_dir: Path, registry_override: Path | None = None) -> Lockfile:
    """Programmatischer Einstiegspunkt: löst auf und schreibt das Lockfile."""
    ctx = WorkspaceContext.load(project_dir, registry_override=registry_override)
    graph = Resolver(ctx.registry).resolve(ctx.manifest)
    lockfile = build_lockfile(target=graph.target, resolutions=list(graph.resolutions))
    lockfile.write(ctx.lockfile_path)
    return lockfile


def lock_command(
    project_dir: Path | None = typer.Option(  # noqa: B008
        None,
        "--project",
        "-p",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Projekt-Verzeichnis mit speccify.yaml (Default: aktuelles Verzeichnis).",
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
    """Löst Dependencies via MVS auf und schreibt speccify.lock (ohne Codegen-Aufruf)."""
    project = project_dir or Path.cwd()
    try:
        lockfile = run_lock(project, registry_override=registry)
    except (ManifestError, RegistryError, ResolverError, FileNotFoundError) as exc:
        typer.echo(f"✗ speccify lock fehlgeschlagen: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"✓ Lockfile geschrieben ({len(lockfile.entries)} Specs) → "
        f"{(project / 'speccify.lock').resolve()}"
    )
