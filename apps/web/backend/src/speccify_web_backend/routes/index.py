"""`GET /api/v1/index` — discovery across the configured index sources.

Query parameters:

- `q` (optional): search term; empty lists everything.
- `source` (optional, repeatable): override the index sources (local directory
  or `git+<url>`). Without it, `SPECCIFY_INDEX` applies.

Response (200): `{query, sources, hits: [...]}`.

This is how the viewer — and any agent over HTTP — finds playbooks without a
central search service; the source is always a git repository.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from speccify_core import GitRepoCache, SpecIndexError, load_indexes, search_index

router = APIRouter(prefix="/api/v1", tags=["index"])


@router.get("/index")
def search_indexes(
    request: Request,
    q: str = Query("", description="search term; empty lists everything"),  # noqa: B008
    source: list[str] | None = Query(None, description="override index sources"),  # noqa: B008
) -> dict[str, Any]:
    settings = request.app.state.settings
    raw_sources = list(source) if source else list(settings.index_sources)
    if not raw_sources:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "no_index_configured",
                "message": (
                    "No index source configured — set `SPECCIFY_INDEX` or pass `?source=`."
                ),
            },
        )
    sources: list[str | Path] = [
        value if value.startswith("git+") else Path(value) for value in raw_sources
    ]
    try:
        entries = load_indexes(sources, cache=GitRepoCache(cache_dir=settings.git_cache_dir))
    except SpecIndexError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "index_invalid", "message": str(exc)},
        ) from exc
    return {
        "query": q,
        "sources": raw_sources,
        "hits": [entry.to_dict() for entry in search_index(entries, q)],
    }
