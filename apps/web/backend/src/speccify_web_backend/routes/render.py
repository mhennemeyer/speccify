"""`POST /api/v1/render` — render a spec via the offline replay cache.

Request body: `{spec_id, version, spec_yaml, target}`.
Response (200): `{spec_id, target, files, generator_pin}`.

Error mapping (matches the CLI/MCP error vocabulary):

- 400 `unknown_target` — `target` not in `SUPPORTED_TARGETS`.
- 400 `spec_invalid`   — YAML parse error or schema-shape error from core.
- 400 `bad_request`    — malformed `version` (not semver) etc.
- 422 `cache_miss`     — `ReplayCacheClient(offline=True)` missed; the body
                         carries a hint telling maintainers how to record the
                         missing entry.
"""

from __future__ import annotations

from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from speccify_core import CacheMissError, CodegenError, SpecLoaderError

from speccify_web_backend.services.render import (
    RenderServiceResult,
    UnknownTargetError,
    render_spec_from_yaml,
)

router = APIRouter(prefix="/api/v1", tags=["render"])


class RenderRequest(BaseModel):
    spec_id: str = Field(..., description="e.g. '@org/button'")
    version: str = Field(..., description="semver, e.g. '0.1.1'")
    spec_yaml: str = Field(..., description="raw YAML source of the spec")
    target: str = Field(..., description="codegen target, e.g. 'react'")


@router.post("/render")
def render_spec(payload: RenderRequest, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings

    # Early YAML validation — easier error than letting react_llm choke later.
    try:
        yaml.safe_load(payload.spec_yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "spec_invalid",
                "message": "Spec YAML did not parse.",
                "details": str(exc),
            },
        ) from exc

    try:
        result: RenderServiceResult = render_spec_from_yaml(
            payload.spec_yaml.encode("utf-8"),
            spec_id=payload.spec_id,
            version=payload.version,
            target=payload.target,
            cache_dir=settings.cache_dir,
        )
    except UnknownTargetError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "unknown_target", "message": str(exc)},
        ) from exc
    except CacheMissError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "cache_miss",
                "message": (
                    "No replay-cache entry for this spec. The playground runs offline in Phase 1d."
                ),
                "hint": (
                    "Maintainers: record the missing entry with "
                    "`uv run python scripts/record_llm_cache.py` against the "
                    "edited spec, then commit the resulting "
                    "tests/fixtures/llm-cache/<hash>.json file."
                ),
                "cause": str(exc),
            },
        ) from exc
    except (SpecLoaderError, CodegenError) as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "spec_invalid", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        # Version.parse / Spec-Id validation in core
        raise HTTPException(
            status_code=400,
            detail={"error_code": "bad_request", "message": str(exc)},
        ) from exc

    return result.to_dict()
