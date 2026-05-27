"""`speccify add`: fügt eine Dependency in `speccify.yaml` ein und ruft intern `lock`.

Default-Range bei `add @scope/name` ist `^<major.minor>` der höchsten Registry-Version.
Mit explizitem `@<range>` (Caret oder exakt) wird die Range übernommen.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer
from speccify_core import (
    LocalRegistry,
    ProjectManifest,
    Resolver,
    ResolverError,
    Workspace,
    WorkspaceError,
    build_lockfile,
)
from speccify_core.manifest import ManifestError
from speccify_core.registry import RegistryError

from speccify_cli.commands._workspace import (
    LOCKFILE_FILENAME,
    MANIFEST_FILENAME,
    WorkspaceContext,
)

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


def _resolve_workspace_target_dir(
    project_dir: Path,
    member: str | None,
    cwd: Path,
) -> tuple[Path, Path]:
    """Bestimmt für einen Workspace-Root das Ziel-Member-Verzeichnis + Root-Verzeichnis.

    Stage-0-Decision (Phase 4): explizites `--member` schlägt CWD-Detection; ohne
    Flag wird das Member aus `cwd` abgeleitet (muss innerhalb eines Member-Dirs
    liegen). Im Root selbst ohne `--member` → Fehler.
    """
    workspace = Workspace.load(project_dir)
    members_by_name = {
        Path(m.relative_path).parent.name: (project_dir / m.relative_path).parent
        for m in workspace.members
    }
    if member is not None:
        if member not in members_by_name:
            available = ", ".join(sorted(members_by_name)) or "(keine)"
            raise WorkspaceError(
                f"Workspace-Member '{member}' nicht gefunden. Verfügbar: {available}."
            )
        return members_by_name[member], project_dir

    # CWD-Detection: ist `cwd` (oder ein Vorfahr) ein Member-Dir?
    cwd_resolved = cwd.resolve()
    for member_dir in members_by_name.values():
        member_resolved = member_dir.resolve()
        if cwd_resolved == member_resolved or member_resolved in cwd_resolved.parents:
            return member_dir, project_dir
    raise WorkspaceError(
        "Im Workspace-Root ohne `--member` und ohne CWD-Member-Kontext: "
        f"`speccify add` braucht `--member <name>` (verfügbar: "
        f"{', '.join(sorted(members_by_name)) or '(keine)'})."
    )


def run_add(
    spec_ref: str,
    project_dir: Path,
    registry_override: Path | None = None,
    *,
    member: str | None = None,
    cwd: Path | None = None,
) -> ProjectManifest:
    spec_id, explicit_range = _parse_spec_ref(spec_ref)

    # Workspace-Modus: in Member-Manifest schreiben, dann Root-Lock neu bauen.
    manifest_path = project_dir / MANIFEST_FILENAME
    if manifest_path.is_file():
        try:
            root_manifest = ProjectManifest.load(manifest_path)
        except ManifestError:
            root_manifest = None
    else:
        root_manifest = None

    if root_manifest is not None and root_manifest.is_workspace_root:
        member_dir, root_dir = _resolve_workspace_target_dir(
            project_dir, member, cwd or Path.cwd()
        )
        return _run_workspace_add(
            spec_id,
            explicit_range,
            member_dir=member_dir,
            workspace_root=root_dir,
            registry_override=registry_override,
        )

    # Single-Project-Pfad (unverändert).
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
        targets=ctx.manifest.targets,
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


def _run_workspace_add(
    spec_id: str,
    explicit_range: str | None,
    *,
    member_dir: Path,
    workspace_root: Path,
    registry_override: Path | None,
) -> ProjectManifest:
    """Schreibt Spec in Member-Manifest, dann Workspace-Root-Lock neu (Stage-0-Decision)."""
    member_ctx = WorkspaceContext.load(member_dir, registry_override=registry_override)

    if explicit_range is not None:
        new_range = explicit_range
    else:
        available = member_ctx.registry.list_versions(spec_id)
        if not available:
            raise RegistryError(
                f"Spec '{spec_id}' ist im Registry {member_ctx.registry.root} nicht verfügbar."
            )
        latest = available[-1]
        new_range = f"^{latest.major}.{latest.minor}"

    deps = dict(member_ctx.manifest.dependencies)
    deps[spec_id] = new_range
    new_manifest = ProjectManifest(
        schema_version=member_ctx.manifest.schema_version,
        targets=member_ctx.manifest.targets,
        dependencies=deps,
        registry_path=member_ctx.manifest.registry_path,
        source_path=member_ctx.manifest.source_path,
    )
    new_manifest.write(member_ctx.manifest_path)

    # Root-Lock neu aufbauen (aggregiert über alle Member inkl. dem soeben aktualisierten).
    workspace = Workspace.load(workspace_root)
    if registry_override is not None:
        registry_path = registry_override.resolve()
    else:
        registry_path = workspace.root_manifest.resolved_registry_path()
    lockfile = workspace.lock(LocalRegistry(registry_path))
    lockfile.write(workspace_root / LOCKFILE_FILENAME)
    return new_manifest


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
    member: str | None = typer.Option(  # noqa: B008
        None,
        "--member",
        "-m",
        help="Workspace-Member (Verzeichnisname unter dem Glob), in dessen speccify.yaml geschrieben wird. "
        "Default: CWD-Detection (Member, in dem du gerade stehst).",
    ),
) -> None:
    """Fügt eine Spec-Dependency in speccify.yaml ein und aktualisiert speccify.lock."""
    project = project_dir or Path.cwd()
    try:
        manifest = run_add(
            spec_ref,
            project,
            registry_override=registry,
            member=member,
            cwd=Path.cwd(),
        )
    except (
        ManifestError,
        RegistryError,
        ResolverError,
        FileNotFoundError,
        WorkspaceError,
    ) as exc:
        typer.echo(f"✗ speccify add fehlgeschlagen: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"✓ {spec_ref} hinzugefügt; Manifest enthält {len(manifest.dependencies)} Dependencies."
    )
