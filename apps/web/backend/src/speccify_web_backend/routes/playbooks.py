"""Playbook routes: list, read, read one step, fetch an asset, validate.

The viewer speaks HTTP, agents speak MCP, humans speak CLI — all three go
through the same core, so none of them can drift.
"""

from __future__ import annotations

import base64
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from speccify_core import (
    LibraryError,
    LocalLibrary,
    Version,
    parse_playbook,
    parse_uses_entry,
    validate_playbook,
)

router = APIRouter(prefix="/api/v1", tags=["playbooks"])


class PlaybookYamlPayload(BaseModel):
    playbook_yaml: str = Field(..., description="raw YAML source of a playbook")


def _source_dict(playbook, source_id: str) -> dict[str, Any]:
    source = playbook.source(source_id)
    if source is None:
        return {"id": source_id, "title": source_id, "url": "", "retrieved": ""}
    return {
        "id": source.id,
        "title": source.title,
        "url": source.url,
        "retrieved": source.retrieved,
        "note": source.note,
    }


def _step_dict(playbook, step) -> dict[str, Any]:
    return {
        "id": step.id,
        "title": step.title,
        "detail": step.detail,
        "uses": step.uses,
        "verify": step.verify,
        "assets": list(step.assets),
        "sources": [_source_dict(playbook, s) for s in step.sources],
    }


def _detail(bundle) -> dict[str, Any]:
    playbook = parse_playbook(bundle.parsed())
    return {
        "id": playbook.id,
        "source": bundle.source_id,
        "version": playbook.version,
        "title": playbook.title,
        "summary": playbook.summary,
        "applies_to": {
            "platforms": list(playbook.applies_to.platforms),
            "requires": list(playbook.applies_to.requires),
            "keywords": list(playbook.applies_to.keywords),
        },
        "prerequisites": list(playbook.prerequisites),
        "steps": [_step_dict(playbook, step) for step in playbook.steps],
        "sources": [_source_dict(playbook, s.id) for s in playbook.sources],
        "pitfalls": list(playbook.pitfalls),
        "acceptance": [
            {"given": a.given, "when": a.when, "then": a.then} for a in playbook.acceptance
        ],
        "assets": list(bundle.asset_paths),
        "uses": list(playbook.uses),
        "yaml": bundle.playbook_bytes.decode("utf-8"),
    }


def _library(request: Request):
    return request.app.state.settings.library()


@router.get("/playbooks")
def list_playbooks(request: Request) -> dict[str, Any]:
    """Every playbook in the local library — the viewer's list."""
    settings = request.app.state.settings
    if not settings.library_path.is_dir():
        return {"playbooks": []}
    library = LocalLibrary(settings.library_path)
    playbooks = []
    for playbook_id, version in library.list_playbooks():
        bundle = library.fetch(playbook_id, version)
        parsed = parse_playbook(bundle.parsed())
        playbooks.append(
            {
                "id": parsed.id,
                "source": bundle.source_id,
                "version": str(version),
                "title": parsed.title,
                "summary": parsed.summary,
                "keywords": list(parsed.applies_to.keywords),
                "platforms": list(parsed.applies_to.platforms),
                "steps": len(parsed.steps),
            }
        )
    return {"playbooks": playbooks}


@router.get("/playbook")
def get_playbook(
    request: Request,
    source: str,
    version: str | None = None,
) -> dict[str, Any]:
    """One playbook by id or git source, with sources resolved per step."""
    try:
        playbook_id, _ = parse_uses_entry(source)
        library = _library(request)
        versions = library.list_versions(playbook_id)
        if not versions:
            raise LibraryError(f"'{playbook_id}' is not available.")
        chosen = Version.parse(version) if version else versions[-1]
        bundle = library.fetch(playbook_id, chosen)
    except LibraryError as exc:
        raise HTTPException(
            status_code=404, detail={"error_code": "not_found", "message": str(exc)}
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error_code": "bad_request", "message": str(exc)}
        ) from exc
    return _detail(bundle)


@router.get("/playbook/asset")
def get_asset(
    request: Request,
    source: str,
    path: str = Query(..., description="bundle-relative asset path"),  # noqa: B008
    version: str | None = None,
) -> dict[str, Any]:
    """An asset's content — text when it decodes, base64 otherwise."""
    try:
        playbook_id, _ = parse_uses_entry(source)
        library = _library(request)
        versions = library.list_versions(playbook_id)
        if not versions:
            raise LibraryError(f"'{playbook_id}' is not available.")
        bundle = library.fetch(playbook_id, Version.parse(version) if version else versions[-1])
        data = bundle.files.get(path)
        if data is None:
            raise LibraryError(f"'{path}' is not part of this bundle.")
    except LibraryError as exc:
        raise HTTPException(
            status_code=404, detail={"error_code": "not_found", "message": str(exc)}
        ) from exc

    try:
        return {"path": path, "encoding": "utf-8", "content": data.decode("utf-8")}
    except UnicodeDecodeError:
        return {
            "path": path,
            "encoding": "base64",
            "content": base64.b64encode(data).decode("ascii"),
        }


@router.post("/validate")
def validate(payload: PlaybookYamlPayload) -> dict[str, Any]:
    """Validate playbook YAML. Content problems are issues, never 4xx."""
    try:
        data = yaml.safe_load(payload.playbook_yaml)
    except yaml.YAMLError as exc:
        return {"ok": False, "issues": [{"path": "$", "message": f"invalid YAML: {exc}"}]}
    issues = validate_playbook(data)
    return {
        "ok": not issues,
        "issues": [{"path": issue.path, "message": issue.message} for issue in issues],
    }
