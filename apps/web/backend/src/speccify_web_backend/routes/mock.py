"""Mock- und Build-Routen — deterministische Codegen-Pfade (kein LLM).

- `POST /api/v1/mock` für eine Registry-Spec.
  Request body: `{spec_id, version?, target?}` (Default-Target `react`,
  Default-Version: neueste in der Registry).
- `POST /api/v1/mock/draft` für einen **ungespeicherten** Entwurf.
  Request body: `{spec_yaml, target?}` — Kinder werden aus der Registry
  aufgelöst. Damit rendert der Composer-Canvas den echten Mock-Output des
  gerade bearbeiteten Dokuments, statt den API-Vertrag nachzuzeichnen.

Response (200, beide): `{spec_id, version, target, files, entry,
template_set, template_version}` — `entry` ist der Modulpfad der Spec selbst
innerhalb von `files`.

- `POST /api/v1/build` baut das komplette Projekt einer `kind: app`-Spec
  (P4, immer Mock-Füllung — Implementierungs-Builds laufen über CLI/MCP).

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
from speccify_core import (
    AppCodegenError,
    CompositionResolutionError,
    MockCodegenError,
    MockUnavailableError,
    RegistryError,
)

from speccify_web_backend.services.mock import (
    UnknownMockTargetError,
    build_app_from_registry,
    mock_draft_spec_yaml,
    mock_spec_from_registry,
)

router = APIRouter(prefix="/api/v1", tags=["mock"])


class MockRequest(BaseModel):
    spec_id: str = Field(..., description="e.g. '@org/search-bar'")
    version: str | None = Field(None, description="semver; default: latest in registry")
    target: str = Field("react", description="mock target (P2: 'react' only)")


class MockDraftRequest(BaseModel):
    spec_yaml: str = Field(..., description="raw YAML source of the unsaved draft")
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
            registry=settings.registry(),
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


@router.post("/mock/draft")
def mock_draft(payload: MockDraftRequest, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    try:
        result = mock_draft_spec_yaml(
            spec_yaml=payload.spec_yaml,
            target=payload.target,
            registry_path=settings.registry_path,
            registry=settings.registry(),
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
    except (CompositionResolutionError, LookupError, RegistryError) as exc:
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


class BuildRequest(BaseModel):
    spec_id: str = Field(..., description="app spec, e.g. '@org/demo-app'")
    version: str | None = Field(None, description="semver; default: latest in registry")
    target: str = Field("react", description="build target (P4: 'react' only)")


@router.post("/build")
def build_app(payload: BuildRequest, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    try:
        result = build_app_from_registry(
            spec_id=payload.spec_id,
            version=payload.version,
            target=payload.target,
            registry_path=settings.registry_path,
            registry=settings.registry(),
        )
    except UnknownMockTargetError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "unknown_target", "message": str(exc)},
        ) from exc
    except (CompositionResolutionError, LookupError, RegistryError) as exc:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "not_found", "message": str(exc)},
        ) from exc
    except (AppCodegenError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "build_failed", "message": str(exc)},
        ) from exc
    return result.to_dict()
