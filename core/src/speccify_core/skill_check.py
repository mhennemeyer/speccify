"""`speccify check` for skills: is this still true, and is it well made?

Three layers, and only the last one needs the network:

* **Specification** — what `skills-ref validate` also enforces. Violations make
  a skill invalid.
* **Best practice** — the official authoring checklist. `skills-ref` does not
  check it and neither does anything else, which is why a description that
  never says *when* to use the skill can sit there for months while the agent
  quietly fails to trigger it.
* **Freshness** — how old the sources are and whether they still resolve. The
  authoring guidance answers decay with "avoid time-sensitive information";
  that is avoidance, not a solution. A source with a retrieval date can be
  checked.

Every finding is either an `error` (this is broken) or a `warning` (this will
bite you). Warnings do not fail a run.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from speccify_core.check import Finding
from speccify_core.skill import (
    BODY_MAX_LINES,
    SKILL_FILENAME,
    STALE_SOURCE_DAYS,
    Skill,
    SkillError,
    parse_skill,
    validate_skill,
)

# A description has to answer "when", because that is all the agent sees before
# deciding whether to load the skill.
_WHEN_RE = re.compile(r"\bwhen\b", re.IGNORECASE)
# The authoring guide is explicit: "Always write in third person." A leading
# "I " or "You " is the failure it names.
_FIRST_PERSON_RE = re.compile(r"^\s*(?:I\b|I'|You\b|You'|We\b|We')", re.IGNORECASE)
# Markdown link to something local (not http, not an anchor).
_LOCAL_LINK_RE = re.compile(r"\[[^\]]*\]\((?!https?:|#|mailto:)(?P<target>[^)\s]+)\)")
_WINDOWS_PATH_RE = re.compile(r"\[[^\]]*\]\((?P<target>[^)\s]*\\[^)\s]*)\)")

_UNKNOWN_AGE = "has no retrieval date, so nobody can tell whether it is still current"


def load_skill(directory: Path) -> tuple[Skill, set[str]]:
    """Read a skill directory. Returns the skill and its bundle-relative files."""
    skill_file = directory / SKILL_FILENAME
    if not skill_file.is_file():
        raise SkillError(f"no {SKILL_FILENAME} in {directory}")
    skill = parse_skill(skill_file.read_text(encoding="utf-8"))
    files = {
        path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file()
    }
    return skill, files


def find_skills(root: Path) -> list[Path]:
    """Every skill directory at or below `root`."""
    if (root / SKILL_FILENAME).is_file():
        return [root]
    return sorted(path.parent for path in root.rglob(SKILL_FILENAME))


def check_skill(
    skill: Skill,
    *,
    directory: Path | None = None,
    bundle_files: set[str] | None = None,
    today: date | None = None,
    stale_days: int = STALE_SOURCE_DAYS,
) -> list[Finding]:
    """Offline check: specification, best practice, source age."""
    findings = [
        Finding("error", issue.path, issue.message)
        for issue in validate_skill(skill, bundle_files=bundle_files)
    ]
    if findings:
        # Everything below assumes a skill that is at least well-formed;
        # piling style notes on top of a broken one is noise.
        return findings

    findings.extend(_check_best_practice(skill, directory=directory, bundle_files=bundle_files))
    findings.extend(check_source_age(skill, today=today or date.today(), stale_days=stale_days))
    if skill.deprecated:
        findings.append(
            Finding(
                "warning",
                "metadata.speccify.deprecated",
                f"this skill was withdrawn by its author: {skill.deprecated}"
                + (f" — use {skill.superseded_by} instead" if skill.superseded_by else ""),
            )
        )
    return findings


def _check_best_practice(
    skill: Skill,
    *,
    directory: Path | None,
    bundle_files: set[str] | None,
) -> list[Finding]:
    findings: list[Finding] = []

    if directory is not None and skill.name != directory.name:
        findings.append(
            Finding(
                "error",
                "name",
                f"is '{skill.name}' but the directory is '{directory.name}' — "
                f"the specification requires them to match",
            )
        )

    if not _WHEN_RE.search(skill.description):
        findings.append(
            Finding(
                "warning",
                "description",
                "never says *when* to use this skill. It is the only thing an agent sees "
                "before deciding to load it, so it has to name the trigger, not just the "
                "subject.",
            )
        )
    if _FIRST_PERSON_RE.match(skill.description):
        findings.append(
            Finding(
                "warning",
                "description",
                "is written in first or second person. It is injected into the system "
                "prompt, where 'I can help you…' reads as the model's own voice and hurts "
                "matching — write it in third person.",
            )
        )

    lines = skill.body.count("\n") + 1
    if lines > BODY_MAX_LINES:
        findings.append(
            Finding(
                "warning",
                "$",
                f"the body is {lines} lines; the guidance is under {BODY_MAX_LINES}. "
                f"Move detail into referenced files — they cost nothing until read.",
            )
        )

    for match in _WINDOWS_PATH_RE.finditer(skill.body):
        findings.append(
            Finding(
                "warning",
                "$",
                f"'{match.group('target')}' uses backslashes; forward slashes work "
                f"everywhere, backslashes break on Unix.",
            )
        )

    # A reference the agent cannot read is worse than no reference: it will try.
    if bundle_files is not None:
        for match in _LOCAL_LINK_RE.finditer(skill.body):
            target = match.group("target").split("#", 1)[0].strip()
            if not target or target in bundle_files:
                continue
            findings.append(
                Finding("error", "$", f"references '{target}', which is not in the skill directory")
            )

    findings.extend(_check_reference_depth(skill, directory=directory))
    return findings


def _check_reference_depth(skill: Skill, *, directory: Path | None) -> list[Finding]:
    """Referenced files must not reference further files.

    The guidance: "Keep references one level deep from SKILL.md." Deeper chains
    get partially read — the agent previews with `head` instead of reading the
    whole file, and then acts on half the information.
    """
    if directory is None:
        return []
    findings: list[Finding] = []
    for match in _LOCAL_LINK_RE.finditer(skill.body):
        target = match.group("target").split("#", 1)[0].strip()
        if not target.endswith(".md"):
            continue
        referenced = directory / target
        if not referenced.is_file():
            continue
        nested = [
            m.group("target")
            for m in _LOCAL_LINK_RE.finditer(
                referenced.read_text(encoding="utf-8", errors="replace")
            )
            if m.group("target").endswith(".md")
        ]
        if nested:
            findings.append(
                Finding(
                    "warning",
                    "$",
                    f"'{target}' itself references {', '.join(sorted(set(nested))[:3])} — "
                    f"keep references one level deep from {SKILL_FILENAME}, or the agent "
                    f"reads them only partially.",
                )
            )
    return findings


def check_source_age(
    skill: Skill,
    *,
    today: date,
    stale_days: int = STALE_SOURCE_DAYS,
) -> list[Finding]:
    """Warn about sources that have not been re-read in a long time."""
    findings: list[Finding] = []
    for index, source in enumerate(skill.sources):
        path = f"$.sources[{index}]"
        if source.retrieved is None:
            findings.append(Finding("warning", path, f"'{source.title}' {_UNKNOWN_AGE}"))
            continue
        age = source.age_days(today=today)
        if age is None:
            findings.append(
                Finding(
                    "error", path, f"retrieved date is not a valid ISO date: '{source.retrieved}'"
                )
            )
            continue
        if age < 0:
            findings.append(
                Finding("warning", path, f"retrieved date is {abs(age)} days in the future")
            )
        elif age > stale_days:
            findings.append(
                Finding(
                    "warning",
                    path,
                    f"last retrieved {age} days ago ({source.retrieved}) — re-read "
                    f"'{source.title}' and update the date, or fix what changed",
                )
            )
    return findings


def check_skill_directory(
    directory: Path,
    *,
    links: bool = False,
    today: date | None = None,
    stale_days: int = STALE_SOURCE_DAYS,
    transport: Any = None,
) -> list[Finding]:
    """Everything, for one skill on disk."""
    from speccify_core.check import check_links

    try:
        skill, files = load_skill(directory)
    except SkillError as exc:
        return [Finding("error", "$", str(exc))]

    findings = check_skill(
        skill, directory=directory, bundle_files=files, today=today, stale_days=stale_days
    )
    if links and not any(f.is_error for f in findings):
        findings.extend(check_links(skill.sources, transport=transport))
    return findings


__all__ = [
    "check_skill",
    "check_skill_directory",
    "check_source_age",
    "find_skills",
    "load_skill",
]
