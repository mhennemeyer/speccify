"""`speccify search`: Specs in Discovery-Indizes finden (Phase P5 Stufe 3).

Kein zentraler Suchdienst — ein Index ist ein Git-Repo (oder ein lokales
Verzeichnis) mit einer Datei pro Spec-Repo. Quellen werden in dieser
Reihenfolge bestimmt (Entscheidung D21):

1. `--index` (mehrfach angebbar),
2. `SPECCIFY_INDEX` (mehrere Quellen mit `,` getrennt — nicht mit `:`, das
   steckt in jeder Git-URL),
3. `./index`, wenn es existiert.

`--json` liefert dieselben Treffer maschinenlesbar — Agents brauchen keinen
Tabellen-Parser.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from speccify_core import GitRepoCache, SpecIndexError, load_indexes, search_index

from speccify_cli.commands._workspace import git_cache_dir

INDEX_ENV = "SPECCIFY_INDEX"
DEFAULT_INDEX_DIR = "index"


def resolve_index_sources(
    explicit: list[str] | None,
    *,
    project_dir: Path | None = None,
) -> list[str | Path]:
    """Index-Quellen nach der dokumentierten Reihenfolge."""
    if explicit:
        return [_as_source(value) for value in explicit]
    from_env = os.environ.get(INDEX_ENV, "").strip()
    if from_env:
        # Trennzeichen ist bewusst nur das Komma: `os.pathsep` ist auf POSIX ein
        # Doppelpunkt und der steckt in jeder Git-URL.
        return [_as_source(value.strip()) for value in from_env.split(",") if value.strip()]
    local = (project_dir or Path.cwd()) / DEFAULT_INDEX_DIR
    return [local] if local.is_dir() else []


def _as_source(value: str) -> str | Path:
    return value if value.startswith("git+") else Path(value)


def run_search(
    query: str,
    *,
    sources: list[str | Path],
    offline: bool = False,
) -> list[dict[str, object]]:
    """Programmatischer Einstiegspunkt: liefert die Treffer als Dicts."""
    cache = GitRepoCache(cache_dir=git_cache_dir(), offline=offline)
    entries = load_indexes(sources, cache=cache)
    return [entry.to_dict() for entry in search_index(entries, query)]


def search_command(
    query: str = typer.Argument("", help="Suchbegriff (leer: alle Einträge listen)."),
    index: list[str] = typer.Option(  # noqa: B008
        None,
        "--index",
        help="Index-Quelle: lokales Verzeichnis oder 'git+<url>'. Mehrfach angebbar.",
    ),
    offline: bool = typer.Option(
        False,
        "--offline/--no-offline",
        help="Nur den lokalen Index-Cache lesen, kein Netz.",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Treffer als JSON ausgeben (für Agents/Skripte).",
    ),
) -> None:
    """Sucht Specs in den konfigurierten Discovery-Indizes."""
    sources = resolve_index_sources(list(index) if index else None)
    if not sources:
        typer.echo(
            "Keine Index-Quelle konfiguriert. Entweder `--index <verzeichnis|git+url>` "
            f"angeben, `{INDEX_ENV}` setzen oder ein `./{DEFAULT_INDEX_DIR}`-Verzeichnis anlegen.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        hits = run_search(query, sources=sources, offline=offline)
    except SpecIndexError as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if as_json:
        typer.echo(json.dumps({"query": query, "hits": hits}, ensure_ascii=False, indent=2))
        return

    if not hits:
        typer.echo(f"Keine Treffer für {query!r} in {len(sources)} Index-Quelle(n).")
        return

    for hit in hits:
        keywords = ", ".join(hit["keywords"]) if hit["keywords"] else "—"
        typer.echo(f"{hit['title']}  [{hit['kind'] or 'spec'}]")
        typer.echo(f"  {hit['source']}")
        typer.echo(f"  {hit['summary']}")
        typer.echo(f"  Keywords: {keywords}")
    typer.echo(f"\n{len(hits)} Treffer. Hinzufügen mit: speccify add <quelle>")
