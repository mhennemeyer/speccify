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
    ASSET_DIRS,
    BODY_MAX_LINES,
    SKILL_FILENAME,
    STALE_SOURCE_DAYS,
    Skill,
    SkillError,
    parse_skill,
    validate_skill,
)
from speccify_core.tool import TOOL_FILENAME, TOOLS_DIR, Tool, ToolError, parse_tool, validate_tool

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
# A bundled file that is a program, not a document. Programs are what fails to
# travel between machines — the reason tool specs exist.
_SCRIPT_SUFFIXES = frozenset({".sh", ".bash", ".zsh", ".ps1", ".py", ".js", ".ts", ".rb"})


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
    tools: dict[str, Tool | ToolError] | None = None,
) -> list[Finding]:
    """Offline check: specification, best practice, source age, tool specs.

    `tools` maps the directory name under `tools/` to the parsed spec — or to
    the error that kept it from parsing. See `load_tools`.
    """
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
    if tools is not None:
        findings.extend(check_tools(tools, bundle_files=bundle_files))
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


def load_tools(directory: Path) -> dict[str, Tool | ToolError]:
    """Every `tools/<name>/TOOL.md` of a skill, parsed — or the reason it did not parse."""
    root = directory / TOOLS_DIR
    if not root.is_dir():
        return {}
    found: dict[str, Tool | ToolError] = {}
    for tool_dir in sorted(p for p in root.iterdir() if (p / TOOL_FILENAME).is_file()):
        try:
            text = (tool_dir / TOOL_FILENAME).read_text(encoding="utf-8")
            found[tool_dir.name] = parse_tool(text)
        except ToolError as exc:
            found[tool_dir.name] = exc
    return found


def tools_from_bundle(files: dict[str, bytes]) -> dict[str, Tool | ToolError]:
    """Same as `load_tools`, for a bundle already in memory."""
    found: dict[str, Tool | ToolError] = {}
    for path, data in sorted(files.items()):
        parts = path.split("/")
        if len(parts) == 3 and parts[0] == TOOLS_DIR and parts[2] == TOOL_FILENAME:
            try:
                found[parts[1]] = parse_tool(data.decode("utf-8"))
            except (ToolError, UnicodeDecodeError) as exc:
                found[parts[1]] = ToolError(str(exc))
    return found


def check_tools(
    tools: dict[str, Tool | ToolError],
    *,
    bundle_files: set[str] | None = None,
) -> list[Finding]:
    """Tool specs: valid, and complete enough to be a contract.

    The spec exists so that an agent on another machine can *write* the tool
    and then *prove* it did so correctly. Both need the examples; the second
    also needs to know what the tool is allowed to touch.
    """
    findings: list[Finding] = []
    for dir_name, tool in tools.items():
        prefix = f"{TOOLS_DIR}/{dir_name}"
        if isinstance(tool, ToolError):
            findings.append(Finding("error", prefix, str(tool)))
            continue
        issues = validate_tool(tool)
        findings.extend(Finding("error", f"{prefix}/{i.path}", i.message) for i in issues)
        if issues:
            continue
        if tool.name != dir_name:
            findings.append(
                Finding(
                    "error",
                    f"{prefix}/name",
                    f"is '{tool.name}' but the directory is '{dir_name}' — they must match",
                )
            )
        if not tool.examples:
            findings.append(
                Finding(
                    "warning",
                    f"{prefix}/$",
                    "has no `## Examples`. The examples are the contract — without them "
                    "nobody can check an implementation written on another machine.",
                )
            )
        if not tool.effects:
            findings.append(
                Finding(
                    "warning",
                    f"{prefix}/effects",
                    "is missing. Say what the tool reads, writes and runs — that is what "
                    "a reviewer looks at before letting an agent implement it.",
                )
            )

    if bundle_files is not None:
        findings.extend(_check_unspecified_scripts(tools, bundle_files))
    return findings


def _check_unspecified_scripts(
    tools: dict[str, Tool | ToolError], bundle_files: set[str]
) -> list[Finding]:
    """A shipped script with no spec is exactly the thing that does not travel."""
    findings: list[Finding] = []
    for path in sorted(bundle_files):
        parts = path.split("/")
        if len(parts) != 2 or parts[0] not in ASSET_DIRS:
            continue
        stem, suffix = Path(parts[1]).stem, Path(parts[1]).suffix
        if suffix not in _SCRIPT_SUFFIXES or stem in tools:
            continue
        findings.append(
            Finding(
                "warning",
                path,
                f"is a script with no tool spec. Scripts break on the next machine "
                f"(Python version, shell, paths); a spec in {TOOLS_DIR}/{stem}/{TOOL_FILENAME} "
                f"lets the agent there write its own.",
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
        skill,
        directory=directory,
        bundle_files=files,
        today=today,
        stale_days=stale_days,
        tools=load_tools(directory),
    )
    if links and not any(f.is_error for f in findings):
        findings.extend(check_links(skill.sources, transport=transport))
    return findings


__all__ = [
    "check_skill",
    "check_skill_directory",
    "check_source_age",
    "check_tools",
    "find_skills",
    "load_skill",
    "load_tools",
    "tools_from_bundle",
]
