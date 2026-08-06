"""`speccify search`: find playbooks in discovery indexes.

No central search service — an index is a git repository (or a local
directory) with one file per playbook repository. Sources are resolved in this
order:

1. `--index` (repeatable),
2. `SPECCIFY_INDEX` (comma-separated — not colon, that lives in every git URL),
3. `./index`, when it exists.

`--json` returns the same hits machine-readably; agents should not have to
parse a table.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from speccify_core import GitRepoCache, SpecIndexError, load_indexes, search_index

from speccify_cli.commands._context import git_cache_dir

INDEX_ENV = "SPECCIFY_INDEX"
DEFAULT_INDEX_DIR = "index"


def resolve_index_sources(
    explicit: list[str] | None,
    *,
    project_dir: Path | None = None,
) -> list[str | Path]:
    """Index sources, in the documented order."""
    if explicit:
        return [_as_source(value) for value in explicit]
    from_env = os.environ.get(INDEX_ENV, "").strip()
    if from_env:
        # Comma only on purpose: `os.pathsep` is a colon on POSIX, and that
        # appears in every git URL.
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
    """Programmatic entry point: hits as plain dicts."""
    cache = GitRepoCache(cache_dir=git_cache_dir(), offline=offline)
    entries = load_indexes(sources, cache=cache)
    return [entry.to_dict() for entry in search_index(entries, query)]


def search_command(
    query: str = typer.Argument("", help="Search term (empty lists everything)."),
    index: list[str] = typer.Option(  # noqa: B008
        None,
        "--index",
        help="Index source: local directory or 'git+<url>'. Repeatable.",
    ),
    offline: bool = typer.Option(
        False,
        "--offline/--no-offline",
        help="Only read the local index cache, never the network.",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Emit hits as JSON (for agents and scripts).",
    ),
) -> None:
    """Search playbooks in the configured discovery indexes."""
    sources = resolve_index_sources(list(index) if index else None)
    if not sources:
        typer.echo(
            "No index source configured. Pass `--index <directory|git+url>`, set "
            f"`{INDEX_ENV}`, or create a `./{DEFAULT_INDEX_DIR}` directory.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        hits = run_search(query, sources=sources, offline=offline)
    except SpecIndexError as exc:
        typer.echo(f"x {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if as_json:
        typer.echo(json.dumps({"query": query, "hits": hits}, ensure_ascii=False, indent=2))
        return

    if not hits:
        typer.echo(f"No hits for {query!r} across {len(sources)} index source(s).")
        return

    for hit in hits:
        keywords = ", ".join(hit["keywords"]) if hit["keywords"] else "-"
        typer.echo(f"{hit['title']}  [{hit['kind'] or 'playbook'}]")
        typer.echo(f"  {hit['source']}")
        typer.echo(f"  {hit['summary']}")
        typer.echo(f"  keywords: {keywords}")
    typer.echo(f"\n{len(hits)} hit(s). Add one with: speccify add <source>")
