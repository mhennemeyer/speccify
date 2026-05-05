"""Entry-Point für das `flowcation`-CLI."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from flowcation_core import SchemaValidator, SpecLoader, SpecLoaderError

app = typer.Typer(
    name="flowcation",
    help="Flowcation CLI — Spec-First Komponenten-Plattform.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root() -> None:
    """Flowcation — Spec-First Komponenten-Plattform."""


@app.command("lint")
def lint(
    files: list[Path] = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Pfade zu flowcation.yaml-Specs.",
    ),
    schema: Path | None = typer.Option(  # noqa: B008
        None,
        "--schema",
        help="Optionaler Pfad zu einem alternativen JSON-Schema "
        "(Default: schema/spec.schema.json).",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
) -> None:
    """Validiert eine oder mehrere YAML-Specs gegen das Spec-Schema v0."""

    validator = SchemaValidator(schema_path=schema)
    total_errors = 0
    failed_files = 0

    for file_path in files:
        try:
            data = SpecLoader.load(file_path)
        except SpecLoaderError as exc:
            typer.echo(f"✗ {file_path}: {exc}", err=True)
            total_errors += 1
            failed_files += 1
            continue

        issues = validator.iter_issues(data)
        if not issues:
            typer.echo(f"✓ {file_path}")
            continue

        failed_files += 1
        typer.echo(f"✗ {file_path}", err=True)
        for issue in issues:
            typer.echo(f"    {issue.format()}", err=True)
            total_errors += 1

    if failed_files:
        typer.echo(
            f"\n{failed_files} Datei(en) mit {total_errors} Problem(en).",
            err=True,
        )
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    sys.exit(app())
