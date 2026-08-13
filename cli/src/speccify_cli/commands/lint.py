"""`speccify lint`: validate skill directories against the specification.

Only what makes a skill *invalid* — the same ground the official reference
validator covers. Everything about whether a skill is any good lives in
`speccify check`.
"""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core.skill import SkillError, validate_skill
from speccify_core.skill_check import find_skills, load_skill


def lint_skill(directory: Path) -> list[str]:
    """Validate one skill directory; returns formatted issues."""
    try:
        skill, files = load_skill(directory)
    except SkillError as exc:
        return [f"$: {exc}"]
    return [issue.format() for issue in validate_skill(skill, bundle_files=files)]


def lint_command(
    paths: list[Path] = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        readable=True,
        help="Skill directories (or a directory tree containing them).",
    ),
) -> None:
    """Validate skills against the Agent Skills specification."""
    targets: list[Path] = []
    for path in paths:
        targets += find_skills(path if path.is_dir() else path.parent)
    if not targets:
        typer.echo("No skills found.", err=True)
        raise typer.Exit(code=1)

    failed = 0
    for directory in targets:
        issues = lint_skill(directory)
        if not issues:
            typer.echo(f"ok  {directory}")
            continue
        failed += 1
        typer.echo(f"fail {directory}", err=True)
        for issue in issues:
            typer.echo(f"     {issue}", err=True)

    if failed:
        typer.echo(f"\n{failed} of {len(targets)} skills have problems.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"\n{len(targets)} skill(s) validated.")
