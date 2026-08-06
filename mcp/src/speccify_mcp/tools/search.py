"""`search` tool: find playbooks in discovery indexes.

Thin adapter over `speccify_core.spec_index` with the same semantics as
`speccify search`. A missing or broken index is a structured result, not an
MCP error.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

INDEX_ENV = "SPECCIFY_INDEX"
DEFAULT_INDEX_DIRNAME = "index"


@dataclass(frozen=True)
class SearchResult:
    """Structured result of the `search` tool."""

    ok: bool
    hits: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "hits": list(self.hits),
            "sources": list(self.sources),
            "code": self.code,
            "message": self.message,
        }


def resolve_sources(project_root: Path, explicit: list[str] | None) -> list[str]:
    """`index_sources` > `SPECCIFY_INDEX` > `<project_root>/index`."""
    if explicit:
        return list(explicit)
    from_env = os.environ.get(INDEX_ENV, "").strip()
    if from_env:
        return [part.strip() for part in from_env.split(",") if part.strip()]
    local = project_root / DEFAULT_INDEX_DIRNAME
    return [str(local)] if local.is_dir() else []


def run_search(
    project_root: Path,
    *,
    query: str = "",
    index_sources: list[str] | None = None,
    offline: bool = False,
) -> SearchResult:
    """Search the configured index sources."""
    from speccify_cli.commands._context import git_cache_dir
    from speccify_core import GitRepoCache, SpecIndexError, load_indexes, search_index

    raw_sources = resolve_sources(project_root, index_sources)
    if not raw_sources:
        return SearchResult(
            ok=False,
            code="no_index_configured",
            message=(
                f"No index source configured — pass `index_sources`, set `{INDEX_ENV}`, "
                f"or create an `index/` directory in the project."
            ),
        )
    sources: list[str | Path] = [
        value if value.startswith("git+") else Path(value) for value in raw_sources
    ]
    try:
        entries = load_indexes(
            sources, cache=GitRepoCache(cache_dir=git_cache_dir(), offline=offline)
        )
    except SpecIndexError as exc:
        return SearchResult(ok=False, sources=raw_sources, code="index_invalid", message=str(exc))
    return SearchResult(
        ok=True,
        hits=[entry.to_dict() for entry in search_index(entries, query)],
        sources=raw_sources,
    )
