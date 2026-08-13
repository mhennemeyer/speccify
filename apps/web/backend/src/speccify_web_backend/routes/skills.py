"""Skill routes: list, read, fetch a bundled file, validate.

The viewer speaks HTTP, agents speak MCP, humans speak CLI — all three go
through the same core, so none of them can drift.

The detail payload leads with `markdown`: that is the skill itself, the text
an agent would follow. Everything beside it (steps, sources) is inferred and
exists so the viewer can show structure without the human reading all of it.
"""

from __future__ import annotations

import base64
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from speccify_core import LibraryError, Version, parse_uses_entry
from speccify_core.skill import parse_skill
from speccify_core.skill_check import check_skill
from speccify_core.skill_library import LocalSkillLibrary

router = APIRouter(prefix="/api/v1", tags=["playbooks"])


class SkillMarkdownPayload(BaseModel):
    skill_markdown: str = Field(..., description="raw SKILL.md source")


def _detail(bundle) -> dict[str, Any]:
    skill = bundle.skill()
    return {
        "id": skill.qualified_id,
        "name": skill.name,
        "source": bundle.source_id,
        "version": skill.version,
        "description": skill.description,
        "license": skill.license,
        "compatibility": skill.compatibility,
        "stack": list(skill.stack),
        "platforms": list(skill.platforms),
        "uses": list(skill.uses),
        "deprecated": skill.deprecated,
        "superseded_by": skill.superseded_by,
        # The skill itself. The viewer renders this; the rest is navigation.
        "markdown": skill.body,
        "steps": [
            {"number": step.number, "title": step.title, "verify": step.verify}
            for step in skill.steps
        ],
        "sources": [
            {"title": s.title, "url": s.url, "retrieved": s.retrieved} for s in skill.sources
        ],
        "files": sorted(path for path in bundle.files if path != "SKILL.md"),
        # The raw file, for the proposal diff.
        "raw": bundle.files["SKILL.md"].decode("utf-8"),
    }


def _library(request: Request):
    return request.app.state.settings.library()


@router.get("/skills")
def list_skills(request: Request) -> dict[str, Any]:
    """Every skill in the local library — the viewer's list.

    Shallow on purpose: the list is for choosing, not for reading.
    """
    settings = request.app.state.settings
    if not settings.library_path.is_dir():
        return {"skills": []}
    library = LocalSkillLibrary(settings.library_path)
    skills = []
    for skill_id, version in library.list_playbooks():
        bundle = library.fetch(skill_id, version)
        skill = bundle.skill()
        skills.append(
            {
                "id": skill.qualified_id,
                "name": skill.name,
                "source": bundle.source_id,
                "version": str(version),
                "description": skill.description,
                "stack": list(skill.stack),
                "platforms": list(skill.platforms),
                "uses": list(skill.uses),
                "deprecated": skill.deprecated,
                "steps": len(skill.steps),
            }
        )
    return {"skills": skills}


@router.get("/skill")
def get_skill(
    request: Request,
    source: str,
    version: str | None = None,
) -> dict[str, Any]:
    """One skill by id or git source, markdown included."""
    try:
        skill_id, _ = parse_uses_entry(source)
        library = _library(request)
        versions = library.list_versions(skill_id)
        if not versions:
            raise LibraryError(f"'{skill_id}' is not available.")
        chosen = Version.parse(version) if version else versions[-1]
        bundle = library.fetch(skill_id, chosen)
    except LibraryError as exc:
        raise HTTPException(
            status_code=404, detail={"error_code": "not_found", "message": str(exc)}
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error_code": "bad_request", "message": str(exc)}
        ) from exc
    return _detail(bundle)


@router.get("/skill/file")
def get_asset(
    request: Request,
    source: str,
    path: str = Query(..., description="bundle-relative asset path"),  # noqa: B008
    version: str | None = None,
) -> dict[str, Any]:
    """An asset's content — text when it decodes, base64 otherwise."""
    try:
        skill_id, _ = parse_uses_entry(source)
        library = _library(request)
        versions = library.list_versions(skill_id)
        if not versions:
            raise LibraryError(f"'{skill_id}' is not available.")
        bundle = library.fetch(skill_id, Version.parse(version) if version else versions[-1])
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
def validate(payload: SkillMarkdownPayload) -> dict[str, Any]:
    """Validate a `SKILL.md`. Content problems are findings, never 4xx.

    Both layers at once: the specification (what makes it invalid) and the
    authoring guidance (what makes it not work well). The viewer shows them
    apart by level.
    """
    from speccify_core.skill import SkillError

    try:
        skill = parse_skill(payload.skill_markdown)
    except SkillError as exc:
        return {"ok": False, "findings": [{"level": "error", "path": "$", "message": str(exc)}]}

    findings = check_skill(skill)
    return {
        "ok": not any(finding.is_error for finding in findings),
        "findings": [
            {"level": finding.level, "path": finding.path, "message": finding.message}
            for finding in findings
        ],
    }
