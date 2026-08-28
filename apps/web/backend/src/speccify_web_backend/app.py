"""FastAPI app factory.

Phase 1d Step 1: wires the `/api/v1/specs` and `/api/v1/render` routers and
attaches a resolved `Settings` instance to `app.state` so routes can read
paths without touching globals. CORS is opened for the Next.js dev server
on `http://localhost:3000` (Step 2 will lock this down further).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from speccify_web_backend.routes import index as index_route
from speccify_web_backend.routes import session as session_route
from speccify_web_backend.routes import skills as skills_route
from speccify_web_backend.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(
        title="speccify-web-backend",
        version="0.0.0",
        description=(
            "Thin FastAPI adapter over speccify-core for the browser playground. "
            "Offline-only in Phase 1d."
        ),
    )
    app.state.settings = settings if settings is not None else Settings.from_env()

    app.add_middleware(
        CORSMiddleware,
        # 3000: Next.js-Playground · 5173: lokale Vite-Dev-Server ·
        # tauri://localhost: Tauri-Shells.
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "tauri://localhost",
        ],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(skills_route.router)
    app.include_router(session_route.router)
    app.include_router(index_route.router)

    return app
