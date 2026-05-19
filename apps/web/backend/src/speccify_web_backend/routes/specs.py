"""`GET /api/v1/specs` — list reference specs from the local pseudo-registry.

The browser playground uses this to populate its spec-picker. We pick the
local registry (not `<repo>/specs/`) on purpose: the registry is the source
that has matching replay-cache entries, so every listed spec also renders
in the MVP. Future phases (registry backend) will route this through HTTP.
"""

from __future__ import annotations

from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Request
from speccify_core import LocalRegistry, RegistryError

router = APIRouter(prefix="/api/v1", tags=["specs"])


@router.get("/specs")
def list_specs(request: Request) -> dict[str, list[dict[str, Any]]]:
    """Return one entry per `(scope, name)` with its latest version + raw YAML.

    Shape: `{"specs": [{"id": "@org/button", "version": "0.1.1",
                        "title": "Button", "yaml": "..."}]}`.
    """
    settings = request.app.state.settings
    registry_path = settings.registry_path
    if not registry_path.is_dir():
        # Treat a missing registry as "no specs available" rather than 500 —
        # makes local dev forgiving when the repo isn't checked out fully.
        return {"specs": []}

    try:
        registry = LocalRegistry(registry_path)
    except RegistryError as exc:  # pragma: no cover — guarded by is_dir above
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    entries: list[dict[str, Any]] = []
    for scope_dir in sorted(p for p in registry_path.iterdir() if p.is_dir()):
        for name_dir in sorted(p for p in scope_dir.iterdir() if p.is_dir()):
            spec_id = f"@{scope_dir.name}/{name_dir.name}"
            versions = registry.list_versions(spec_id)
            if not versions:
                continue
            latest = versions[-1]
            spec = registry.fetch(spec_id, latest)
            yaml_text = spec.raw_bytes.decode("utf-8")
            title = _extract_title(yaml_text) or spec_id
            entries.append(
                {
                    "id": spec_id,
                    "version": str(latest),
                    "title": title,
                    "yaml": yaml_text,
                }
            )
    return {"specs": entries}


def _extract_title(yaml_text: str) -> str | None:
    """Pull `title:` from the spec YAML — best-effort, never raises."""
    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return None
    if not isinstance(parsed, dict):
        return None
    title = parsed.get("title")
    return str(title) if isinstance(title, str) else None
