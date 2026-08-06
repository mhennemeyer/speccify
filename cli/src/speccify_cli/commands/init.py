"""`speccify init`: start a project that uses playbooks."""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core import MANIFEST_FILENAME, ProjectManifest


def run_init(project_dir: Path) -> Path:
    """Write a minimal manifest; returns its path."""
    manifest_path = project_dir / MANIFEST_FILENAME
    if manifest_path.exists():
        raise FileExistsError(f"{manifest_path} already exists.")
    project_dir.mkdir(parents=True, exist_ok=True)
    ProjectManifest().write(manifest_path)
    return manifest_path


def init_command(
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
) -> None:
    """Create a speccify.yaml for a project that consumes playbooks."""
    try:
        path = run_init(project_dir)
    except FileExistsError as exc:
        typer.echo(f"x {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"ok {path}")
    typer.echo("Next: speccify add <playbook-id-or-git-source>")
