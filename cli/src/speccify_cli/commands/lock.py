"""`speccify lock`: resolve the manifest and pin every bundle."""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core import (
    Lockfile,
    ManifestError,
    RegistryError,
    Resolver,
    ResolverError,
    build_lockfile,
)

from speccify_cli.commands._context import ProjectContext


def run_lock(project_dir: Path, library_override: Path | None = None) -> Lockfile:
    context = ProjectContext.load(project_dir, library_override=library_override)
    graph = Resolver(context.libraries).resolve(context.manifest)
    lockfile = build_lockfile(list(graph.resolutions))
    lockfile.write(context.lockfile_path)
    return lockfile


def lock_command(
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
    library: Path | None = typer.Option(  # noqa: B008
        None, "--library", help="Local playbook library (default: from the manifest)."
    ),
) -> None:
    """Resolve dependencies and write speccify.lock."""
    try:
        lockfile = run_lock(project_dir, library)
    except (ResolverError, RegistryError, ManifestError, FileNotFoundError) as exc:
        typer.echo(f"x speccify lock failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for entry in lockfile.entries:
        pinned = f" @ {entry.source_commit[:12]}" if entry.source_commit else ""
        typer.echo(f"ok {entry.id}@{entry.version} via {entry.resolved_via}{pinned}")
    typer.echo(f"\n{len(lockfile.entries)} playbook(s) pinned.")
