"""FastAPI app factory.

Step 0 ships a minimal app with only a healthcheck so the workspace integration
can be verified. Routes for `/api/v1/specs` and `/api/v1/render` arrive in
Step 1.
"""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="speccify-web-backend",
        version="0.0.0",
        description=(
            "Thin FastAPI adapter over speccify-core for the browser playground. "
            "Offline-only in Phase 1d."
        ),
    )

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
