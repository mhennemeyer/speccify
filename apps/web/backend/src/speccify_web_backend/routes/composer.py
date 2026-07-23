"""Composer-Routen (P3): Spec-Detail, Validierung, Speichern.

Der Composer ist agent-bedienbar: jede UI-Aktion existiert als HTTP-Endpoint,
der Zustand ist die Spec-YAML in der lokalen Registry (Round-Trip).

- `GET  /api/v1/specs/{scope}/{name}?version=` — Detail inkl. API-Contract-JSON,
  Komposition und aufgelösten Kind-Contracts (für Canvas/Property-Panel/Wiring).
- `POST /api/v1/validate` mit `{spec_yaml}` — `{ok, issues[]}` (Schema v1 +
  Kompositions-Typprüfung gegen die Registry). Nie 4xx für inhaltliche Fehler.
- `POST /api/v1/specs` mit `{spec_yaml}` — validiert + schreibt in die Registry
  (Pfad aus `id`/`version`); 422 `validation_failed` mit Issues bei Fehlern.
  Gespeicherte Composites erscheinen sofort in der Palette → Komposition ist
  rekursiv.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from speccify_core import RegistryError

from speccify_web_backend.services.composer import (
    SpecValidationFailed,
    save_spec_yaml,
    spec_detail,
    validate_spec_yaml,
)

router = APIRouter(prefix="/api/v1", tags=["composer"])


class SpecYamlPayload(BaseModel):
    spec_yaml: str = Field(..., description="raw YAML source of the spec")


@router.get("/specs/{scope}/{name}")
def get_spec_detail(
    scope: str, name: str, request: Request, version: str | None = None
) -> dict[str, Any]:
    settings = request.app.state.settings
    try:
        return spec_detail(
            registry_path=settings.registry_path,
            spec_id=f"@{scope}/{name}",
            version=version,
        )
    except (LookupError, RegistryError) as exc:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "not_found", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "bad_request", "message": str(exc)},
        ) from exc


@router.post("/validate")
def validate_spec(payload: SpecYamlPayload, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    outcome = validate_spec_yaml(
        payload.spec_yaml.encode("utf-8"),
        registry_path=settings.registry_path,
    )
    return outcome.to_dict()


@router.post("/specs")
def save_spec(payload: SpecYamlPayload, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    try:
        return save_spec_yaml(
            payload.spec_yaml.encode("utf-8"),
            registry_path=settings.registry_path,
        )
    except SpecValidationFailed as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "validation_failed", "issues": exc.issues},
        ) from exc
