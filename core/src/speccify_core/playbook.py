"""Playbook model: parse and validate `playbook.yaml`.

A playbook is the unit Speccify distributes: an ordered workflow with the
sources it was researched from, the assets it needs and the pitfalls you would
otherwise hit twice. It is written for coding agents — the knowledge an agent
would otherwise re-derive on every run.

This module stays I/O-free apart from reading the JSON schema: it parses a
mapping and reports problems as structured issues. Loading bundles from disk or
git is the registry's job.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

DEFAULT_PLAYBOOK_SCHEMA_PATH: Path = (
    Path(__file__).resolve().parents[3] / "schema" / "playbook.schema.json"
)
PLAYBOOK_FILENAME = "playbook.yaml"
ASSET_DIR = "assets"

# `speccify check` warns beyond this; sources age, and a playbook with stale
# links is worse than no playbook.
STALE_SOURCE_DAYS = 180


class PlaybookError(ValueError):
    """A playbook could not be parsed."""


@dataclass(frozen=True)
class Issue:
    """A finding, addressable by JSON path."""

    path: str
    message: str

    def format(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str
    retrieved: str
    note: str | None = None

    @property
    def retrieved_date(self) -> date | None:
        try:
            return date.fromisoformat(self.retrieved)
        except ValueError:
            return None

    def age_days(self, *, today: date) -> int | None:
        retrieved = self.retrieved_date
        return None if retrieved is None else (today - retrieved).days


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    detail: str = ""
    uses: str | None = None
    sources: tuple[str, ...] = ()
    assets: tuple[str, ...] = ()
    verify: str | None = None

    @property
    def is_delegated(self) -> bool:
        """True when this step is handled by another playbook."""
        return self.uses is not None


@dataclass(frozen=True)
class Acceptance:
    given: str | None = None
    when: str | None = None
    then: str | None = None


@dataclass(frozen=True)
class AppliesTo:
    platforms: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class Playbook:
    id: str
    version: str
    title: str
    summary: str
    steps: tuple[Step, ...]
    sources: tuple[Source, ...] = ()
    pitfalls: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    acceptance: tuple[Acceptance, ...] = ()
    applies_to: AppliesTo = field(default_factory=AppliesTo)
    authors: tuple[str, ...] = ()
    license: str | None = None

    def step(self, step_id: str) -> Step | None:
        return next((s for s in self.steps if s.id == step_id), None)

    def source(self, source_id: str) -> Source | None:
        return next((s for s in self.sources if s.id == source_id), None)

    @property
    def uses(self) -> tuple[str, ...]:
        """References to other playbooks, in step order and without duplicates."""
        seen: dict[str, None] = {}
        for step in self.steps:
            if step.uses is not None:
                seen.setdefault(step.uses, None)
        return tuple(seen)

    @property
    def asset_paths(self) -> tuple[str, ...]:
        """Every asset referenced by any step, sorted and deduplicated."""
        return tuple(sorted({asset for step in self.steps for asset in step.assets}))


_VALIDATOR: Draft202012Validator | None = None


def _validator() -> Draft202012Validator:
    global _VALIDATOR
    if _VALIDATOR is None:
        schema = json.loads(DEFAULT_PLAYBOOK_SCHEMA_PATH.read_text(encoding="utf-8"))
        _VALIDATOR = Draft202012Validator(schema)
    return _VALIDATOR


def normalize(data: Any) -> Any:
    """Make YAML conveniences match the schema.

    Authors write `retrieved: 2026-08-06` without quotes, and PyYAML hands that
    back as a `date`. Rejecting it would be pedantry, so dates are normalised to
    ISO strings before validation.
    """
    if isinstance(data, date):
        return data.isoformat()
    if isinstance(data, dict):
        return {key: normalize(value) for key, value in data.items()}
    if isinstance(data, list):
        return [normalize(item) for item in data]
    return data


def schema_issues(data: Any) -> list[Issue]:
    """Validate against the JSON schema only (structure, types, patterns)."""
    errors = sorted(_validator().iter_errors(normalize(data)), key=lambda e: list(e.absolute_path))
    return [
        Issue(
            "$" + "".join(f".{p}" if isinstance(p, str) else f"[{p}]" for p in e.absolute_path),
            e.message,
        )
        for e in errors
    ]


def parse_playbook(data: Any) -> Playbook:
    """Turn a validated mapping into a `Playbook`. Raises `PlaybookError` if it cannot."""
    if not isinstance(data, dict):
        raise PlaybookError("A playbook must be a YAML mapping.")
    data = normalize(data)
    issues = schema_issues(data)
    if issues:
        raise PlaybookError("; ".join(issue.format() for issue in issues[:5]))

    applies_raw = data.get("applies_to") or {}
    return Playbook(
        id=str(data["id"]),
        version=str(data["version"]),
        title=str(data["title"]),
        summary=str(data["summary"]).strip(),
        steps=tuple(
            Step(
                id=str(raw["id"]),
                title=str(raw["title"]),
                detail=str(raw.get("detail", "")),
                uses=str(raw["uses"]) if raw.get("uses") else None,
                sources=tuple(str(s) for s in raw.get("sources", ())),
                assets=tuple(str(a) for a in raw.get("assets", ())),
                verify=str(raw["verify"]) if raw.get("verify") else None,
            )
            for raw in data["steps"]
        ),
        sources=tuple(
            Source(
                id=str(raw["id"]),
                title=str(raw["title"]),
                url=str(raw["url"]),
                retrieved=str(raw["retrieved"]),
                note=str(raw["note"]) if raw.get("note") else None,
            )
            for raw in data.get("sources", ())
        ),
        pitfalls=tuple(str(p) for p in data.get("pitfalls", ())),
        prerequisites=tuple(str(p) for p in data.get("prerequisites", ())),
        acceptance=tuple(
            Acceptance(
                given=raw.get("given"),
                when=raw.get("when"),
                then=raw.get("then"),
            )
            for raw in data.get("acceptance", ())
        ),
        applies_to=AppliesTo(
            platforms=tuple(str(p) for p in applies_raw.get("platforms", ())),
            requires=tuple(str(r) for r in applies_raw.get("requires", ())),
            keywords=tuple(str(k) for k in applies_raw.get("keywords", ())),
        ),
        authors=tuple(str(a) for a in data.get("authors", ())),
        license=str(data["license"]) if data.get("license") else None,
    )


def validate_playbook(data: Any, *, bundle_files: set[str] | None = None) -> list[Issue]:
    """Full validation: schema plus the cross-references the schema cannot express.

    `bundle_files` are the bundle-relative paths that exist next to the
    `playbook.yaml`; when given, referenced assets are checked against them.
    """
    data = normalize(data)
    issues = schema_issues(data)
    if issues:
        return issues

    playbook = parse_playbook(data)

    step_ids: set[str] = set()
    for index, step in enumerate(playbook.steps):
        path = f"$.steps[{index}]"
        if step.id in step_ids:
            issues.append(Issue(path, f"Duplicate step id '{step.id}'."))
        step_ids.add(step.id)
        if step.uses is not None and step.detail:
            issues.append(
                Issue(
                    path,
                    "A step either delegates via `uses` or describes itself via `detail`, "
                    "not both — otherwise it is unclear which one an agent should follow.",
                )
            )
        if step.uses is None and not step.detail:
            issues.append(
                Issue(path, "A step needs either `detail` or `uses`; an empty step helps nobody.")
            )
        for source_id in step.sources:
            if playbook.source(source_id) is None:
                issues.append(Issue(f"{path}.sources", f"Unknown source '{source_id}'."))
        if bundle_files is not None:
            for asset in step.assets:
                if asset not in bundle_files:
                    issues.append(
                        Issue(f"{path}.assets", f"Asset '{asset}' is not part of the bundle.")
                    )

    source_ids: set[str] = set()
    for index, source in enumerate(playbook.sources):
        path = f"$.sources[{index}]"
        if source.id in source_ids:
            issues.append(Issue(path, f"Duplicate source id '{source.id}'."))
        source_ids.add(source.id)
        if source.retrieved_date is None:
            issues.append(
                Issue(path, f"`retrieved` is not a valid ISO date: '{source.retrieved}'.")
            )

    referenced = {source_id for step in playbook.steps for source_id in step.sources}
    for index, source in enumerate(playbook.sources):
        if source.id not in referenced:
            issues.append(
                Issue(
                    f"$.sources[{index}]",
                    f"Source '{source.id}' is not referenced by any step — "
                    f"either wire it into a step or drop it.",
                )
            )

    return issues


__all__ = [
    "ASSET_DIR",
    "DEFAULT_PLAYBOOK_SCHEMA_PATH",
    "PLAYBOOK_FILENAME",
    "STALE_SOURCE_DAYS",
    "Acceptance",
    "AppliesTo",
    "Issue",
    "Playbook",
    "PlaybookError",
    "Source",
    "normalize",
    "Step",
    "parse_playbook",
    "schema_issues",
    "validate_playbook",
]
