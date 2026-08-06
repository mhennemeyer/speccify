"""`speccify verify`: does the lockfile still describe reality?"""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core import (
    Lockfile,
    LockfileError,
    RegistryError,
    Resolver,
    ResolverError,
    Version,
    bundle_sha256,
)

from speccify_cli.commands._context import ProjectContext, fetch_bundle


def run_verify(
    project_dir: Path,
    *,
    library_override: Path | None = None,
    offline: bool = False,
) -> list[str]:
    """Compare manifest, lockfile and the actual bundles; returns problems."""
    problems: list[str] = []
    context = ProjectContext.load(project_dir, library_override=library_override, offline=offline)
    if not context.lockfile_path.is_file():
        return [f"No lockfile in {project_dir}. Run `speccify lock` first."]
    lockfile = Lockfile.load(context.lockfile_path)

    try:
        graph = Resolver(context.libraries).resolve(context.manifest)
    except (ResolverError, RegistryError) as exc:
        return [str(exc)]

    resolved = {r.playbook_id: r for r in graph.resolutions}
    locked = {e.id: e for e in lockfile.entries}
    for playbook_id in sorted(set(locked) - set(resolved)):
        problems.append(f"'{playbook_id}' is in the lockfile but no longer resolved.")
    for playbook_id in sorted(set(resolved) - set(locked)):
        problems.append(f"'{playbook_id}' resolves but is missing from the lockfile.")

    for playbook_id in sorted(set(locked) & set(resolved)):
        entry, resolution = locked[playbook_id], resolved[playbook_id]
        if str(resolution.version) != entry.version:
            problems.append(
                f"{playbook_id}: version drift — lockfile {entry.version}, "
                f"resolved {resolution.version}."
            )
            continue
        try:
            bundle = fetch_bundle(context.libraries, entry.id, Version.parse(entry.version))
        except RegistryError as exc:
            problems.append(str(exc))
            continue
        actual = bundle_sha256(bundle.files)
        if actual != entry.bundle_sha256:
            problems.append(
                f"{playbook_id}@{entry.version}: bundle hash drift — "
                f"lockfile {entry.bundle_sha256}, actual {actual}."
            )
        if entry.source_commit and bundle.source_commit != entry.source_commit:
            problems.append(
                f"{playbook_id}@{entry.version}: commit drift — lockfile "
                f"{entry.source_commit[:12]}, actual {(bundle.source_commit or '?')[:12]}. "
                f"A tag was moved."
            )
    return problems


def verify_command(
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
    library: Path | None = typer.Option(  # noqa: B008
        None, "--library", help="Local playbook library (default: from the manifest)."
    ),
    offline: bool = typer.Option(
        False, "--offline/--no-offline", help="Only read cached git sources, never the network."
    ),
) -> None:
    """Check that the lockfile still matches the manifest and the actual bundles."""
    try:
        problems = run_verify(project_dir, library_override=library, offline=offline)
    except (LockfileError, FileNotFoundError) as exc:
        typer.echo(f"x speccify verify failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if problems:
        for problem in problems:
            typer.echo(f"x {problem}", err=True)
        typer.echo(f"\n{len(problems)} problem(s).", err=True)
        raise typer.Exit(code=1)
    typer.echo("ok lockfile, manifest and bundles agree.")
