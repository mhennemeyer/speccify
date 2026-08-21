"""`speccify init`: start a project that uses skills.

Three things, all idempotent: the manifest, the `.gitignore` line for the
upstream cache, and the link that makes the agent look at `.agent/skills/`.
"""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core import MANIFEST_FILENAME, ProjectManifest
from speccify_core.expansion import AGENT_DIR

from speccify_cli.commands.expand import SPECCIFY_DIR
from speccify_cli.commands.link import run_link

CACHE_IGNORE = f"{AGENT_DIR}/{SPECCIFY_DIR}/cache/"


def run_init(project_dir: Path) -> Path:
    """Write a minimal manifest, ignore the cache, link the agent; returns the manifest path."""
    manifest_path = project_dir / MANIFEST_FILENAME
    if manifest_path.exists():
        raise FileExistsError(f"{manifest_path} already exists.")
    project_dir.mkdir(parents=True, exist_ok=True)
    ProjectManifest().write(manifest_path)
    _ignore_cache(project_dir / ".gitignore")
    run_link(project_dir)
    return manifest_path


def _ignore_cache(gitignore: Path) -> None:
    existing = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    if CACHE_IGNORE in existing.splitlines():
        return
    separator = "" if not existing or existing.endswith("\n") else "\n"
    gitignore.write_text(
        f"{existing}{separator}# speccify: upstream cache, derived from the lockfile\n"
        f"{CACHE_IGNORE}\n",
        encoding="utf-8",
    )


def init_command(
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
) -> None:
    """Create speccify.yaml, ignore the cache and link .claude/skills to .agent/skills."""
    try:
        path = run_init(project_dir)
    except (FileExistsError, OSError) as exc:
        typer.echo(f"x {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"ok {path}")
    typer.echo("Next: speccify add <skill-id-or-git-source>, then speccify expand")
