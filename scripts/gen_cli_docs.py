"""Generiert die CLI-Reference der Doku-Site aus der `speccify`-Binary.

Die Quelle der Wahrheit ist die Typer-App selbst (`speccify_cli.__main__.app`).
Über die Click-Introspektion (`typer.main.get_command`) werden je Top-Level-
Command Usage + Options/Arguments deterministisch — also ohne Rich-/Terminal-
abhängige Formatierung — in MDX gerendert.

Aufruf:
    python scripts/gen_cli_docs.py            # --write (Default)
    python scripts/gen_cli_docs.py --check     # exit 1 bei Drift

Phase 6 (Landing + Doku-Site), Stage 3.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import click
import typer.main
from speccify_cli.__main__ import app

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CLI_DOCS_DIR = _REPO_ROOT / "apps" / "marketing" / "src" / "content" / "docs" / "cli"

_GENERATED_BANNER = (
    "<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — "
    "nicht von Hand editieren. -->"
)


def _yaml_quote(value: str) -> str:
    """Quotet einen String sicher als doppelt-gequoteten YAML-Scalar."""

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _short_description(command: click.Command) -> str:
    """Einzeilige Beschreibung aus dem Command-Help."""

    text = command.help or command.short_help or ""
    first = text.strip().splitlines()[0] if text.strip() else ""
    return " ".join(first.split())


def _table_escape(value: str) -> str:
    """Escaped Pipes für Markdown-Tabellenzellen."""

    return value.replace("|", "\\|").replace("\n", " ")


def _usage(name: str, command: click.Command) -> str:
    """Deterministische Usage-Zeile (ohne Terminal-Breite)."""

    ctx = click.Context(command, info_name=f"speccify {name}")
    pieces = command.collect_usage_pieces(ctx)
    return " ".join([f"speccify {name}", *pieces])


def _options_table(command: click.Command) -> list[str]:
    """Rendert eine Markdown-Tabelle der Optionen, falls vorhanden."""

    rows: list[str] = []
    for param in command.params:
        if not isinstance(param, click.Option):
            continue
        flags = ", ".join(f"`{opt}`" for opt in param.opts + param.secondary_opts)
        help_text = _table_escape(param.help or "")
        rows.append(f"| {flags} | {help_text} |")
    if not rows:
        return []
    return ["## Options", "", "| Option | Beschreibung |", "| --- | --- |", *rows]


def _arguments_table(command: click.Command) -> list[str]:
    """Rendert eine Markdown-Tabelle der Argumente, falls vorhanden."""

    rows: list[str] = []
    for param in command.params:
        if not isinstance(param, click.Argument):
            continue
        required = "ja" if param.required else "nein"
        rows.append(f"| `{param.name}` | {required} |")
    if not rows:
        return []
    return ["## Arguments", "", "| Argument | Pflicht |", "| --- | --- |", *rows]


def render_command_mdx(name: str, command: click.Command) -> str:
    """Rendert die MDX-Seite eines einzelnen Top-Level-Commands."""

    description = _short_description(command)
    lines: list[str] = [
        "---",
        f"title: {_yaml_quote(f'speccify {name}')}",
    ]
    if description:
        lines.append(f"description: {_yaml_quote(description)}")
    lines.append("---")
    lines.append("")
    lines.append(_GENERATED_BANNER)
    lines.append("")
    if description:
        lines.append(description)
        lines.append("")
    lines.append("## Usage")
    lines.append("")
    lines.append("```bash")
    lines.append(_usage(name, command))
    lines.append("```")

    arguments = _arguments_table(command)
    if arguments:
        lines.append("")
        lines.extend(arguments)

    options = _options_table(command)
    if options:
        lines.append("")
        lines.extend(options)

    return "\n".join(lines).rstrip("\n") + "\n"


def render_index_mdx(commands: dict[str, click.Command]) -> str:
    """Rendert die CLI-Index-Übersichtsseite."""

    lines: list[str] = [
        "---",
        'title: "CLI Reference"',
        'description: "Übersicht aller speccify-Subcommands."',
        "---",
        "",
        _GENERATED_BANNER,
        "",
        "Das `speccify`-CLI bündelt alle Spec-First-Workflows. Jeder Subcommand",
        "hat eine eigene Referenzseite:",
        "",
        "| Command | Beschreibung |",
        "| --- | --- |",
    ]
    for name in sorted(commands):
        description = _table_escape(_short_description(commands[name]))
        lines.append(f"| [`speccify {name}`](/cli/{name}/) | {description} |")
    return "\n".join(lines).rstrip("\n") + "\n"


def _collect_commands() -> dict[str, click.Command]:
    """Liefert die Top-Level-Commands der Typer-App als Click-Commands."""

    cli = typer.main.get_command(app)
    assert isinstance(cli, click.Group)
    return dict(cli.commands)


def _iter_targets() -> list[tuple[Path, str]]:
    """Liefert (Zielpfad, gerendertes-MDX) für Index + alle Commands."""

    commands = _collect_commands()
    targets: list[tuple[Path, str]] = [
        (_CLI_DOCS_DIR / "index.md", render_index_mdx(commands)),
    ]
    for name in sorted(commands):
        targets.append((_CLI_DOCS_DIR / f"{name}.md", render_command_mdx(name, commands[name])))
    return targets


def run_gen(*, check: bool) -> int:
    """Generiert die CLI-Doku. `check=True` schreibt nicht, meldet nur Drift."""

    drift: list[str] = []
    for dest_path, rendered in _iter_targets():
        if check:
            current = dest_path.read_text(encoding="utf-8") if dest_path.exists() else None
            if current != rendered:
                drift.append(str(dest_path.relative_to(_REPO_ROOT)))
            continue
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(rendered, encoding="utf-8")

    if check and drift:
        sys.stderr.write(
            "CLI-Reference ist nicht synchron mit der Binary. Betroffen:\n"
            + "\n".join(f"  - {path}" for path in drift)
            + "\nLauf `python scripts/gen_cli_docs.py` zum Beheben.\n"
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Schreibt nicht; exit 1 wenn die CLI-Doku veraltet ist.",
    )
    args = parser.parse_args(argv)
    return run_gen(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
