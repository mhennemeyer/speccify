"""`speccify link`: point an agent's skills directory at `.agent/skills/`.

Skills live agent-neutrally under `.agent/`; the agent-specific dot folders
only refer to them. Claude Code follows a symlink at `.claude/skills`
(verified 2026-08-21), so a link is all it takes — one place to edit, every
agent sees the same thing.
"""

from __future__ import annotations

import os
from pathlib import Path

import typer
from speccify_core.expansion import SKILLS_DIR

from speccify_cli.commands.expand import AGENT_DIR

# Where each agent looks for project skills, relative to the project.
AGENT_SKILL_DIRS = {"claude": Path(".claude") / "skills"}


def run_link(project_dir: Path, agent: str = "claude") -> Path:
    """Create `<agent skills dir>` → `.agent/skills`; returns the link. Idempotent."""
    try:
        link = project_dir / AGENT_SKILL_DIRS[agent]
    except KeyError as exc:
        raise ValueError(
            f"Unknown agent '{agent}'. Known: {', '.join(sorted(AGENT_SKILL_DIRS))}."
        ) from exc
    target = project_dir / AGENT_DIR / SKILLS_DIR
    target.mkdir(parents=True, exist_ok=True)
    relative = Path(os.path.relpath(target, link.parent))

    if link.is_symlink():
        if Path(os.readlink(link)) == relative:
            return link
        link.unlink()
    elif link.exists():
        if any(link.iterdir()):
            raise FileExistsError(
                f"{link} exists and is not empty. Move its contents to {target} "
                f"(or run `speccify expand`), then remove it and link again."
            )
        link.rmdir()
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(relative, target_is_directory=True)
    return link


def link_command(
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
    agent: str = typer.Option("claude", "--agent", help="Which agent's skills directory to link."),
) -> None:
    """Point the agent's skills directory (.claude/skills) at .agent/skills."""
    try:
        link = run_link(project_dir, agent)
    except (FileExistsError, ValueError, OSError) as exc:
        typer.echo(f"x speccify link failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"ok {link} -> {os.readlink(link)}")
