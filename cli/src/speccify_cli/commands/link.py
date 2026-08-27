"""`speccify link`: point an agent's skills directory at `.agent/skills/`.

Skills live agent-neutrally under `.agent/`; the agent-specific dot folders
only refer to them. Claude Code follows a symlink at `.claude/skills`
(verified 2026-08-21), so a link is all it takes — one place to edit, every
agent sees the same thing.

Windows (D17, plan projektfenster.md): creating a symlink needs Developer
Mode or admin rights, so when `symlink_to` is denied we fall back to a
directory junction — followed by every tool, creatable by every user. Git
without symlink support checks an existing symlink out as a plain text file
holding the target path; `link` recognizes that husk and replaces it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from speccify_core.expansion import SKILLS_DIR

from speccify_cli.commands.expand import AGENT_DIR

# Where each agent looks for project skills, relative to the project.
AGENT_SKILL_DIRS = {"claude": Path(".claude") / "skills"}


def _is_junction(path: Path) -> bool:
    return os.name == "nt" and os.path.isjunction(path)


def _reads_like_link(path: Path, relative: Path) -> bool:
    """True if `path` is git's symlink-as-text-file for `relative`."""
    try:
        if path.stat().st_size > 4096:
            return False
        content = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return False
    return content in {relative.as_posix(), str(relative)}


def _create_junction(link: Path, target: Path) -> None:
    if sys.platform != "win32":  # pragma: no cover — der Fallback ist Windows-only
        raise OSError("Junctions gibt es nur auf Windows.")
    import _winapi

    # Junction-Ziele sind immer absolut — der Link gilt für diese Maschine,
    # nicht fürs Repo (das Repo trägt weiterhin den relativen Symlink).
    _winapi.CreateJunction(str(target.resolve()), str(link))


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
    elif _is_junction(link):
        if link.resolve() == target.resolve():
            return link
        link.rmdir()
    elif link.is_file():
        if _reads_like_link(link, relative):
            link.unlink()
        else:
            raise FileExistsError(
                f"{link} exists and is a file. Expected a link to {target} — "
                f"move the file away, then link again."
            )
    elif link.exists():
        if any(link.iterdir()):
            raise FileExistsError(
                f"{link} exists and is not empty. Move its contents to {target} "
                f"(or run `speccify expand`), then remove it and link again."
            )
        link.rmdir()
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(relative, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        _create_junction(link, target)
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
    try:
        shown = os.readlink(link)
    except OSError:
        shown = str(link.resolve())
    typer.echo(f"ok {link} -> {shown}")
