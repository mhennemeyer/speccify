"""`speccify add`: add a playbook to the manifest and re-lock."""

from __future__ import annotations

import re
from pathlib import Path

import typer
from speccify_core import ManifestError, RegistryError, ResolverError, Version, parse_uses_entry

from speccify_cli.commands._context import ProjectContext, list_versions
from speccify_cli.commands.lock import run_lock

_EXPLICIT_VERSION = re.compile(r"^(?P<id>.+)@(?P<version>\d+\.\d+\.\d+)$")


def run_add(project_dir: Path, reference: str, library_override: Path | None = None) -> str:
    """Add `reference` to the manifest; returns the range that was written."""
    context = ProjectContext.load(project_dir, library_override=library_override)

    match = _EXPLICIT_VERSION.match(reference)
    if match and not reference.startswith("git+"):
        playbook_id, version_raw = match.group("id"), match.group("version")
    elif match:
        playbook_id, version_raw = match.group("id"), match.group("version")
    else:
        playbook_id, _ = parse_uses_entry(reference)
        version_raw = None

    if version_raw is None:
        available = list_versions(context.libraries, playbook_id)
        if not available:
            raise RegistryError(f"'{playbook_id}' is not available locally or as a git source.")
        version = available[-1]
    else:
        version = Version.parse(version_raw)

    range_raw = f"^{version.major}.{version.minor}"
    context.manifest.with_dependency(playbook_id, range_raw).write(context.manifest_path)
    run_lock(project_dir, library_override)
    return range_raw


def add_command(
    reference: str = typer.Argument(
        ..., help="Playbook id ('@scope/name[@X.Y.Z]') or git source ('git+<url>[#<path>]')."
    ),
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
    library: Path | None = typer.Option(  # noqa: B008
        None, "--library", help="Local playbook library (default: from the manifest)."
    ),
) -> None:
    """Add a playbook dependency and update the lockfile."""
    try:
        range_raw = run_add(project_dir, reference, library)
    except (ResolverError, RegistryError, ManifestError, FileNotFoundError, ValueError) as exc:
        typer.echo(f"x speccify add failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"ok added {reference} as {range_raw}")
