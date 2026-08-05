"""`GET /api/v1/index` — Discovery-Suche über die konfigurierten Index-Quellen (P5).

Query-Parameter:

- `q` (optional): Suchbegriff; leer listet alle Einträge.
- `source` (optional, mehrfach): Index-Quelle überschreiben (lokales
  Verzeichnis oder `git+<url>`). Ohne Angabe gelten die Quellen aus
  `SPECCIFY_INDEX`.

Response (200): `{query, sources, hits: [{source, title, summary, kind,
keywords, homepage, license, origin}]}`.

Damit findet auch der Composer (und jeder Agent über HTTP) Specs, ohne dass es
einen zentralen Suchdienst gäbe — die Quelle ist immer ein Git-Repo.
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
                    "Keine Index-Quelle konfiguriert — `SPECCIFY_INDEX` setzen "
                    "oder `?source=` angeben."
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
