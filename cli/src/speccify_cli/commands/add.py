"""`speccify add`: fügt eine Dependency in `speccify.yaml` ein und ruft intern `lock`.

Default-Range bei `add @scope/name` ist `^<major.minor>` der höchsten Registry-Version.
Mit explizitem `@<range>` (Caret oder exakt) wird die Range übernommen.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer
from speccify_core import (
    ProjectManifest,
    Resolver,
    ResolverError,
    build_lockfile,
)
from speccify_core.manifest import ManifestError
from speccify_core.registry import RegistryError

from speccify_cli.commands._workspace import WorkspaceContext

_SPEC_REF_PATTERN = re.compile(
    r"^(?P<id>@[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*)(?:@(?P<range>.+))?$"
)


def _parse_spec_ref(raw: str) -> tuple[str, str | None]:
    match = _SPEC_REF_PATTERN.match(raw)
    if not match:
        raise typer.BadParameter(
            f"Ungültige Spec-Referenz '{raw}': erwartet '@scope/name[@<range>]'."
        )
    return match.group("id"), match.group("range")


def run_add(
    spec_ref: str,
    project_dir: Path,
    registry_override: Path | None = None,
) -> ProjectManifest:
    spec_id, explicit_range = _parse_spec_ref(spec_ref)
    ctx = WorkspaceContext.load(project_dir, registry_override=registry_override)

    if explicit_range is not None:
        new_range = explicit_range
    else:
        available = ctx.registry.list_versions(spec_id)
        if not available:
            raise RegistryError(
                f"Spec '{spec_id}' ist im Registry {ctx.registry.root} nicht verfügbar."
            )
        latest = available[-1]
        new_range = f"^{latest.major}.{latest.minor}"

    deps = dict(ctx.manifest.dependencies)
    deps[spec_id] = new_range
    new_manifest = ProjectManifest(
        schema_version=ctx.manifest.schema_version,
        target=ctx.manifest.target,
        dependencies=deps,
        registry_path=ctx.manifest.registry_path,
        source_path=ctx.manifest.source_path,
    )
    new_manifest.write(ctx.manifest_path)

    # Implizit lock: Manifest neu laden (mit aktualisierten Deps), dann auflösen.
    refreshed = WorkspaceContext.load(project_dir, registry_override=registry_override)
    graph = Resolver(refreshed.registry).resolve(refreshed.manifest)
    lockfile = build_lockfile(target=graph.target, resolutions=list(graph.resolutions))
    lockfile.write(refreshed.lockfile_path)
    return refreshed.manifest


def add_command(
    spec_ref: str = typer.Argument(  # noqa: B008
        ...,
        help="Spec-Referenz: '@scope/name' oder '@scope/name@<range>' (Caret oder exakt).",
    ),
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
    """Fügt eine Spec-Dependency in speccify.yaml ein und aktualisiert speccify.lock."""
    project = project_dir or Path.cwd()
    try:
        manifest = run_add(spec_ref, project, registry_override=registry)
    except (ManifestError, RegistryError, ResolverError, FileNotFoundError) as exc:
        typer.echo(f"✗ speccify add fehlgeschlagen: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"✓ {spec_ref} hinzugefügt; Manifest enthält {len(manifest.dependencies)} Dependencies."
    )
