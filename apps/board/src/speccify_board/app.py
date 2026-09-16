"""FastAPI routes: the board page, one page per repo, JSON, refresh, writes."""

from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from typing import Annotated, Any

from fastapi import Body, Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from speccify_core.board import render_board, summarize

from speccify_board.config import BoardConfig
from speccify_board.mcp_server import build_mcp
from speccify_board.registry import Registry
from speccify_board.sources import SourceError

_basic = HTTPBasic(auto_error=False)


# Module level on purpose: with `from __future__ import annotations` FastAPI
# resolves parameter annotations in the module namespace.
class StationBody(BaseModel):
    station: str
    expected_revision: str | None = None


class TaskBody(BaseModel):
    done: bool
    expected_revision: str | None = None


def create_app(
    config: BoardConfig,
    data_dir: Path,
    *,
    password: str | None = None,
    mcp_token: str | None = None,
    background: bool = True,
) -> FastAPI:
    registry = Registry(config, data_dir)
    mcp = build_mcp(registry, config)
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if background:
            registry.start()
        else:
            registry.refresh_all()
        async with mcp.session_manager.run():
            yield
        registry.stop()

    app = FastAPI(title="speccify-board", version="0.0.0", lifespan=lifespan)
    app.state.registry = registry
    app.state.mcp = mcp

    def require_auth(
        credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)],
    ) -> None:
        if password is None:
            return
        ok = credentials is not None and secrets.compare_digest(
            credentials.password.encode(), password.encode()
        )
        if not ok:
            raise HTTPException(
                status_code=401,
                detail="Passwort nötig (BOARD_PASSWORD).",
                headers={"WWW-Authenticate": "Basic"},
            )

    auth = Depends(require_auth)

    def page(name: str | None) -> HTMLResponse:
        if name is not None and name not in registry.sources:
            raise HTTPException(status_code=404, detail=f"Unbekanntes Repo: {name}")
        specs = registry.specs(name)
        title = config.title if name is None else f"{config.title} · {name}"
        errors = [f"{s['name']}: {s['error']}" for s in registry.status() if s["error"]]
        html = render_board(specs, title=title, source=registry.source_label(), editable=True)
        if errors:
            notice = "".join(
                f'<p style="margin:0 0 8px;color:#b91c1c;font-size:12px">⚠ {escape(e)}</p>'
                for e in errors
            )
            html = html.replace("<main>", "<main>" + notice, 1)
        return HTMLResponse(html)

    @app.get("/", response_class=HTMLResponse, dependencies=[auth])
    def index() -> HTMLResponse:
        return page(None)

    @app.get("/r/{name}/", response_class=HTMLResponse, dependencies=[auth])
    def repo_page(name: str) -> HTMLResponse:
        return page(name)

    @app.get("/api/board.json", dependencies=[auth])
    def board_json() -> dict[str, Any]:
        specs = registry.specs()
        return {
            "title": config.title,
            "repos": registry.status(),
            "summary": summarize(specs),
            "specs": [spec.to_dict() for spec in specs],
        }

    @app.post("/api/refresh", dependencies=[auth])
    def refresh() -> dict[str, Any]:
        registry.refresh_all()
        return {"repos": registry.status()}

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        status = registry.status()
        return {"ok": all(not s["error"] for s in status), "repos": status}

    def source_for(name: str):
        # A workspace entry labels its projects `name/child`; writes address the entry.
        base = name.split("/", 1)[0]
        source = registry.sources.get(base)
        if source is None:
            raise HTTPException(status_code=404, detail=f"Unbekanntes Repo: {name}")
        return source

    @app.post("/api/r/{name:path}/specs/{spec_id}/station", dependencies=[auth])
    def move_station(name: str, spec_id: str, body: Annotated[StationBody, Body()]) -> JSONResponse:
        source = source_for(name)
        try:
            commit = source.move_station(
                spec_id, body.station, source=name, expected_revision=body.expected_revision
            )
        except SourceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        source.refresh()
        return JSONResponse({"ok": True, "commit": commit})

    @app.post("/api/r/{name:path}/specs/{spec_id}/tasks/{index}", dependencies=[auth])
    def toggle_task(
        name: str, spec_id: str, index: int, body: Annotated[TaskBody, Body()]
    ) -> JSONResponse:
        source = source_for(name)
        try:
            commit = source.toggle_task(
                spec_id, index, body.done, source=name, expected_revision=body.expected_revision
            )
        except SourceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        source.refresh()
        return JSONResponse({"ok": True, "commit": commit})

    @app.middleware("http")
    async def no_cache(request: Request, call_next):  # type: ignore[no-untyped-def]
        # Spec 033: /mcp is guarded by its own bearer token, not by the page password.
        if request.url.path.startswith("/mcp") and mcp_token:
            header = request.headers.get("authorization", "")
            given = header[7:] if header.lower().startswith("bearer ") else ""
            if not secrets.compare_digest(given.encode(), mcp_token.encode()):
                return JSONResponse(
                    {"detail": "Bearer-Token nötig (BOARD_MCP_TOKEN)."},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    # Mounted at the root so `/mcp` answers directly (a Mount at "/mcp" would
    # redirect POST /mcp → /mcp/, which not every MCP client follows).
    app.mount("/", mcp_app)
    return app
