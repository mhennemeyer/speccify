"""Skill model: read, write and check `SKILL.md`.

A skill is a directory with a `SKILL.md` at its root — the Agent Skills format
(<https://agentskills.io/specification>). Speccify stores skills in exactly
that format rather than its own. A skill works in any compatible host once it
lands in that host's skills directory (Speccify links Claude and Codex to the
canonical `.agent/skills/`), with or without any of this tooling running.

What Speccify adds lives in the `metadata` map, which the specification
provides for exactly this purpose ("Clients can use this to store additional
properties not defined by the Agent Skills spec"). Two constraints shape the
design:

* `metadata` maps **strings to strings** — nothing nested. Lists are therefore
  comma-separated, and keys are prefixed (`speccify.stack`) as the spec
  recommends for collision safety.
* The body has **no format restrictions**. So structure is *inferred*, never
  required: a skill written by someone else parses fine, it simply yields
  fewer findings. Anything this module cannot infer is absent, not an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import yaml

SKILL_FILENAME = "SKILL.md"
ASSET_DIRS = ("assets", "scripts", "references")
# Everything a bundle may carry beside SKILL.md: the spec's three conventions
# plus Speccify's `tools/` (see `tool.py`).
BUNDLE_DIRS = (*ASSET_DIRS, "tools")

# Speccify's own keys inside the spec's `metadata` map.
META_PREFIX = "speccify."

# Sections that are structure, not a step of the work.
_RESERVED_SECTIONS = frozenset(
    {
        "sources",
        "tools",
        "pitfalls",
        "prerequisites",
        "acceptance",
        "references",
        "see also",
        "notes",
        "examples",
    }
)

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(?P<yaml>.*?)\r?\n---\r?\n?(?P<body>.*)\Z", re.DOTALL)
_HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
_VERIFY_RE = re.compile(r"^\*\*Verify:?\*\*\s*(?P<text>.+?)\s*$", re.MULTILINE | re.IGNORECASE)
# `- [Title](url) — retrieved 2026-08-13`  (em dash or hyphen, "retrieved" optional-ish)
# The URL may contain balanced parentheses — Apple's Swift documentation URLs
# end in `sync()`, and a naive `[^)]+` swallows the link at the first bracket
# and then never sees the retrieval date behind it.
_SOURCE_RE = re.compile(
    r"^\s*[-*]\s*\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^()\s]*(?:\([^()\s]*\)[^()\s]*)*)\)"
    r"(?:\s*[—–-]\s*retrieved\s*(?P<retrieved>\d{4}-\d{2}-\d{2}))?",
    re.MULTILINE | re.IGNORECASE,
)
# A leading number in a heading is a convention, not a requirement.
_STEP_NUMBER_RE = re.compile(r"^\s*(?P<n>\d+)\s*[—–.\-)]\s*(?P<rest>.+)$")

# Spec rules for `name`, quoted from the specification.
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024
# Best-practice guidance, not spec: "Keep your main SKILL.md under 500 lines."
BODY_MAX_LINES = 500

STALE_SOURCE_DAYS = 180


class SkillError(ValueError):
    """A skill could not be parsed."""


@dataclass(frozen=True)
class Issue:
    """A finding, addressable by a location inside the skill."""

    path: str
    message: str

    def format(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass(frozen=True)
class Source:
    """A document this skill was written from."""

    title: str
    url: str
    retrieved: str | None = None

    @property
    def retrieved_date(self) -> date | None:
        if not self.retrieved:
            return None
        try:
            return date.fromisoformat(self.retrieved)
        except ValueError:
            return None

    def age_days(self, *, today: date) -> int | None:
        retrieved = self.retrieved_date
        return None if retrieved is None else (today - retrieved).days


@dataclass(frozen=True)
class Step:
    """One `##` section of the body that reads like a step of the work.

    Inferred, not declared — the spec puts no requirements on the body.
    """

    title: str
    body: str
    number: int | None = None
    verify: str | None = None


@dataclass(frozen=True)
class Skill:
    """A parsed `SKILL.md`."""

    name: str
    description: str
    body: str
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    allowed_tools: str | None = None
    # Keys whose value was a list or mapping. `str()` would turn those into
    # something that looks like data but is not, so they are recorded here and
    # reported by `validate_skill` instead of silently becoming text.
    nested_metadata_keys: tuple[str, ...] = ()

    # --- Speccify's additions, read out of `metadata` ---

    def meta(self, key: str) -> str | None:
        return self.metadata.get(META_PREFIX + key)

    def meta_list(self, key: str) -> tuple[str, ...]:
        """A comma-separated metadata value. `metadata` cannot nest, so lists live as text."""
        raw = self.meta(key)
        return tuple(part.strip() for part in raw.split(",") if part.strip()) if raw else ()

    @property
    def version(self) -> str | None:
        return self.meta("version")

    @property
    def scope(self) -> str | None:
        """`name` may only contain `[a-z0-9-]`, so `@scope/name` cannot live there."""
        return self.meta("scope")

    @property
    def qualified_id(self) -> str:
        scope = self.scope
        return f"@{scope}/{self.name}" if scope else self.name

    @property
    def stack(self) -> tuple[str, ...]:
        return self.meta_list("stack")

    @property
    def platforms(self) -> tuple[str, ...]:
        return self.meta_list("platforms")

    @property
    def uses(self) -> tuple[str, ...]:
        """Other skills this one builds on — what used to make a 'playbook'."""
        return self.meta_list("uses")

    @property
    def deprecated(self) -> str | None:
        """Reason this skill was withdrawn, if it was. See W-H in the plan."""
        return self.meta("deprecated")

    @property
    def superseded_by(self) -> str | None:
        return self.meta("superseded-by")

    # --- Inferred body structure ---

    @property
    def steps(self) -> tuple[Step, ...]:
        return tuple(_parse_steps(self.body))

    @property
    def sources(self) -> tuple[Source, ...]:
        return tuple(_parse_sources(self.body))


def parse_skill(text: str) -> Skill:
    """Parse `SKILL.md` text. Raises `SkillError` when the frontmatter is unusable."""
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise SkillError("SKILL.md must start with YAML frontmatter delimited by `---`.")
    try:
        front = yaml.safe_load(match.group("yaml")) or {}
    except yaml.YAMLError as exc:
        raise SkillError(f"Frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(front, dict):
        raise SkillError("Frontmatter must be a mapping.")

    raw_meta = front.get("metadata") or {}
    if not isinstance(raw_meta, dict):
        raise SkillError("`metadata` must be a mapping of strings to strings.")

    return Skill(
        name=str(front.get("name", "")),
        description=str(front.get("description", "")),
        body=match.group("body"),
        license=_optional_str(front.get("license")),
        compatibility=_optional_str(front.get("compatibility")),
        # Scalars are coerced rather than rejected: `version: 1.0` is a float in
        # YAML, and refusing it would be pedantry against a human who wrote the
        # obvious thing. Lists and mappings are a different matter — see below.
        metadata={str(k): _scalar(v) for k, v in raw_meta.items() if _is_scalar(v)},
        allowed_tools=_optional_str(front.get("allowed-tools")),
        nested_metadata_keys=tuple(str(k) for k, v in raw_meta.items() if not _is_scalar(v)),
    )


def validate_skill(skill: Skill, *, bundle_files: set[str] | None = None) -> list[Issue]:
    """Check against the specification. Violations here make a skill invalid."""
    issues: list[Issue] = []

    if not skill.name:
        issues.append(Issue("name", "is required."))
    else:
        if len(skill.name) > NAME_MAX:
            issues.append(
                Issue("name", f"is {len(skill.name)} characters; the maximum is {NAME_MAX}.")
            )
        if not _NAME_RE.match(skill.name):
            issues.append(
                Issue(
                    "name",
                    "may contain only lowercase letters, numbers and single hyphens, "
                    "and may not start or end with one.",
                )
            )
        for reserved in ("anthropic", "claude"):
            if reserved in skill.name:
                issues.append(Issue("name", f"may not contain the reserved word '{reserved}'."))

    if not skill.description.strip():
        issues.append(Issue("description", "is required and must be non-empty."))
    elif len(skill.description) > DESCRIPTION_MAX:
        issues.append(
            Issue(
                "description",
                f"is {len(skill.description)} characters; the maximum is {DESCRIPTION_MAX}.",
            )
        )

    if skill.compatibility is not None and len(skill.compatibility) > 500:
        issues.append(Issue("compatibility", "is longer than the 500 character maximum."))

    for key in skill.nested_metadata_keys:
        issues.append(
            Issue(
                f"metadata.{key}",
                "must be a string — the specification allows `metadata` to map strings to "
                "strings only. Use a comma-separated value for a list.",
            )
        )

    if bundle_files is not None:
        if SKILL_FILENAME not in bundle_files:
            issues.append(Issue("$", f"a skill directory must contain {SKILL_FILENAME}."))

    return issues


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _is_scalar(value: Any) -> bool:
    return not isinstance(value, (list, dict, tuple, set))


def _scalar(value: Any) -> str:
    """Metadata values are strings; a YAML date or number is written back as text."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def sections(body: str) -> list[tuple[str, str]]:
    """Split the body into `(heading, content)` pairs at `##` level."""
    matches = list(_HEADING_RE.finditer(body))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections.append((match.group("title"), body[match.end() : end].strip()))
    return sections


def _parse_steps(body: str) -> list[Step]:
    steps: list[Step] = []
    for title, content in sections(body):
        if title.strip().lower() in _RESERVED_SECTIONS:
            continue
        number: int | None = None
        clean = title
        numbered = _STEP_NUMBER_RE.match(title)
        if numbered:
            number = int(numbered.group("n"))
            clean = numbered.group("rest").strip()
        verify = _VERIFY_RE.search(content)
        steps.append(
            Step(
                title=clean,
                body=content,
                number=number,
                verify=verify.group("text").strip() if verify else None,
            )
        )
    return steps


def _parse_sources(body: str) -> list[Source]:
    """Sources live in the body, where they also serve the agent reading it.

    The convention is `- [Title](url) — retrieved YYYY-MM-DD`. A source without
    a date parses; the missing date is reported by `check`, not here.
    """
    for title, content in sections(body):
        if title.strip().lower() == "sources":
            return [
                Source(
                    title=match.group("title").strip(),
                    url=match.group("url").strip(),
                    retrieved=match.group("retrieved"),
                )
                for match in _SOURCE_RE.finditer(content)
            ]
    return []


__all__ = [
    "ASSET_DIRS",
    "BUNDLE_DIRS",
    "BODY_MAX_LINES",
    "DESCRIPTION_MAX",
    "Issue",
    "NAME_MAX",
    "SKILL_FILENAME",
    "STALE_SOURCE_DAYS",
    "Skill",
    "SkillError",
    "Source",
    "Step",
    "parse_skill",
    "sections",
    "validate_skill",
]
