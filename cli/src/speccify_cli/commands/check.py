"""`speccify check`: is this skill still true, and is it well made?

Three layers, and only the last needs the network:

* **specification** — what `lint` covers, repeated here so one command answers
  the whole question,
* **best practice** — the official authoring checklist, which no other tool
  enforces,
* **freshness** — how old the sources are and whether they still resolve.

Errors fail the run; warnings report. `--links` is opt-in because it is slow
and a flaky proxy should never fail a normal test run.
"""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core.skill import STALE_SOURCE_DAYS
from speccify_core.skill_check import check_skill_directory, find_skills


def check_command(
    paths: list[Path] = typer.Argument(  # noqa: B008
        ..., exists=True, readable=True, help="Skill directories (or a tree containing them)."
    ),
    links: bool = typer.Option(
        False, "--links/--no-links", help="Also check that every source URL still resolves."
    ),
    stale_days: int = typer.Option(
        STALE_SOURCE_DAYS, "--stale-days", help="Warn about sources older than this."
    ),
) -> None:
    """Check whether skills are still current: source age, dead links, best practice."""
    targets: list[Path] = []
    for path in paths:
        targets += find_skills(path if path.is_dir() else path.parent)
    if not targets:
        typer.echo("No skills found.", err=True)
        raise typer.Exit(code=1)

    errors = warnings = 0
    for directory in targets:
        findings = check_skill_directory(directory, links=links, stale_days=stale_days)
        if not findings:
            typer.echo(f"ok  {directory}")
            continue
        typer.echo(f"--- {directory}")
        for finding in findings:
            typer.echo(f"    {finding.format()}", err=finding.is_error)
            if finding.is_error:
                errors += 1
            else:
                warnings += 1

    summary = f"\n{len(targets)} skill(s): {errors} error(s), {warnings} warning(s)."
    if errors:
        typer.echo(summary, err=True)
        raise typer.Exit(code=1)
    typer.echo(summary)
