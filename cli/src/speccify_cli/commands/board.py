"""`speccify board`: the team board as a self-contained HTML page (Spec 031)."""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core.board import load_specs, render_board, summarize


def board_command(
    out: Path = typer.Option(  # noqa: B008
        Path("board.html"), "--out", "-o", help="Target HTML file (parents are created)."
    ),
    specs: Path | None = typer.Option(  # noqa: B008
        None,
        "--specs",
        help="Specs folder (default: <project>/.agent/specs, i.e. the `specs` branch checkout).",
    ),
    project: Path = typer.Option(Path("."), "--project", help="Project directory."),  # noqa: B008
    title: str | None = typer.Option(  # noqa: B008
        None, "--title", help="Page title (default: project folder name)."
    ),
    source: str | None = typer.Option(  # noqa: B008
        None, "--source", help="Label for the data source shown on the page, e.g. `specs@<commit>`."
    ),
    no_archive: bool = typer.Option(False, "--no-archive", help="Leave `archive/` out."),
) -> None:
    """Render progress from the spec register into one static HTML page."""
    specs_dir = (specs or project / ".agent" / "specs").resolve()
    if not specs_dir.is_dir():
        typer.secho(f"No specs folder: {specs_dir}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    loaded = load_specs(specs_dir, include_archive=not no_archive)
    page = render_board(
        loaded,
        title=title or project.resolve().name,
        source=source or specs_dir.as_posix(),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    summary = summarize(loaded)
    stations = summary["stations"]
    assert isinstance(stations, dict)
    typer.echo(
        f"{out}: {summary['specs']} specs, {summary['tasks_done']}/{summary['tasks_total']} tasks, "
        f"Backlog {stations['Backlog']} · Doing {stations['Doing']} · Done {stations['Done']}"
    )
