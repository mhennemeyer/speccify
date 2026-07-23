"""`POST /api/v1/mock` — deterministische Mock-Closure für eine Registry-Spec.

Request body: `{spec_id, version?, target?}` (Default-Target `react`,
Default-Version: neueste in der Registry).
Response (200): `{spec_id, version, target, files, template_set, template_version}`.

Error mapping (CLI/MCP-Vokabular):

- 400 `unknown_target`    — Target ist nicht `react` (P2-Scope).
- 404 `not_found`         — Spec/Version existiert nicht in der Registry.
- 400 `bad_request`       — kaputte Version/Referenz.
- 422 `mock_unavailable`  — logic-Spec ohne `api.fixtures` (Entscheidung D1).

Vorbau für die Composer-Palette (P3): der Composer holt Mock-Bundles über
diesen Endpoint, ohne LLM im Loop.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from speccify_core import MockCodegenError, MockUnavailableError, RegistryError

from speccify_web_backend.services.mock import (
    UnknownMockTargetError,
    mock_spec_from_registry,
)

router = APIRouter(prefix="/api/v1", tags=["mock"])


class MockRequest(BaseModel):
    spec_id: str = Field(..., description="e.g. '@org/search-bar'")
    version: str | None = Field(None, description="semver; default: latest in registry")
    target: str = Field("react", description="mock target (P2: 'react' only)")


@router.post("/mock")
def mock_spec(payload: MockRequest, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    try:
        result = mock_spec_from_registry(
            spec_id=payload.spec_id,
            version=payload.version,
            target=payload.target,
            registry_path=settings.registry_path,
        )
    except UnknownMockTargetError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "unknown_target", "message": str(exc)},
        ) from exc
    except MockUnavailableError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "mock_unavailable", "message": str(exc)},
        ) from exc
    except (LookupError, RegistryError) as exc:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "not_found", "message": str(exc)},
        ) from exc
    except (MockCodegenError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "bad_request", "message": str(exc)},
        ) from exc
    return result.to_dict()
