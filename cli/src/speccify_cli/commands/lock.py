"""`speccify lock`: löst Manifest-Dependencies auf und schreibt `speccify.lock`.

Phase 3 Stage 5: Wenn das Root-Manifest ein `workspaces:`-Feld hat, wird der
Workspace entdeckt, alle Member-Dependencies aggregiert und genau **ein**
Root-Lockfile (`<root>/speccify.lock`) mit globaler MVS geschrieben
(Cargo-Stil). Andernfalls läuft der Phase-1a-Pfad (Single-Manifest).
"""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core import (
    Lockfile,
    ProjectManifest,
    Resolver,
    ResolverError,
    build_lockfile,
)
from speccify_core.manifest import ManifestError
from speccify_core.registry import RegistryError
from speccify_core.workspace import Workspace, WorkspaceError

from speccify_cli.commands._workspace import (
    LOCKFILE_FILENAME,
    MANIFEST_FILENAME,
    WorkspaceContext,
    build_registries,
)


def _is_workspace_root(project_dir: Path) -> bool:
    manifest_path = project_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return False
    try:
        manifest = ProjectManifest.load(manifest_path)
    except ManifestError:
        return False
    return manifest.is_workspace_root


def _run_workspace_lock(project_dir: Path, registry_override: Path | None) -> Lockfile:
    workspace = Workspace.load(project_dir)
    if registry_override is not None:
        registry_path = registry_override.resolve()
    else:
        registry_path = workspace.root_manifest.resolved_registry_path()
    lockfile = workspace.lock(build_registries(registry_path))
    lockfile.write(project_dir / LOCKFILE_FILENAME)
    return lockfile


def run_lock(project_dir: Path, registry_override: Path | None = None) -> Lockfile:
    """Programmatischer Einstiegspunkt: löst auf und schreibt das Lockfile."""
    if _is_workspace_root(project_dir):
        return _run_workspace_lock(project_dir, registry_override)
    ctx = WorkspaceContext.load(project_dir, registry_override=registry_override)
    graph = Resolver(ctx.registries).resolve(ctx.manifest)
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
    except (
        ManifestError,
        RegistryError,
        ResolverError,
        WorkspaceError,
        FileNotFoundError,
    ) as exc:
        typer.echo(f"✗ speccify lock fehlgeschlagen: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"✓ Lockfile geschrieben ({len(lockfile.entries)} Specs) → "
        f"{(project / 'speccify.lock').resolve()}"
    )
