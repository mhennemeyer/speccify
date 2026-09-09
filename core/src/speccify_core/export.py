"""`speccify export`: the reverse of expand — a project skill goes to a library.

`expand` turns a library skill into *this project's* skill: Speccify metadata
gone, tools project-wide under `.agent/tools/`, a `## In this project`
section at the end. A skill that was born in a project — done three times
here, with tools written here — travels the other way:

* the `## In this project` section is dropped (it is the project's, by
  definition), links into `.agent/tools/` point into the bundle again;
* `metadata.speccify.version` and `speccify.scope` are set, so the skill has
  an id a library can address (`@scope/name`);
* each tool it uses goes along as its **contract** (`TOOL.md`); the
  implementation written here becomes `reference.<ext>` — a hint for the next
  implementer, never the contract. Other platforms' implementations stay.

What no build step can do is *generalise the text*: a bundle id, a path, a
port, a person's name that belongs to this project has to become a
placeholder `<like-this>` or go. `find_suspects` points at the lines that
look like they need that reading — the report is the agent's to-do list, the
same way `expand` reports placeholders to fill.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from speccify_core.expansion import PLATFORMS, PROJECT_HEADING, find_placeholders
from speccify_core.skill import META_PREFIX, SKILL_FILENAME, Skill, parse_skill
from speccify_core.tool import TOOL_FILENAME, TOOLS_DIR

REFERENCE_STEM = "reference"

# Links from an expanded skill into the project-wide tools go back into the bundle.
_PROJECT_TOOLS_LINK_RE = re.compile(r"\]\((?:\.\./)+tools/")
_TOOL_REF_RE = re.compile(
    r"(?:\.\./)+tools/(?P<name>[a-z0-9][a-z0-9-]*)/" + re.escape(TOOL_FILENAME)
)

# Things that are almost always specific to one machine, one team, one app.
_SUSPECT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "path",
        re.compile(r"(?<![\w/.])(?:/Users/|/home/|/Volumes/|/opt/|[A-Za-z]:\\|~/)[^\s`'\")\]>]*"),
    ),
    ("email", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    (
        "bundle-id",
        re.compile(r"\b(?:com|de|io|org|net|app|dev|ch|at|co|eu)\.[a-z0-9-]+(?:\.[a-z0-9-]+)+\b"),
    ),
    (
        "secret",
        re.compile(
            r"(?i)\b(?:token|secret|password|passwd|api[_-]?key|team[_ -]?id|client[_-]?id)\b"
            r"\s*[:=]\s*[^\s`'\"<]+"
        ),
    ),
    ("host", re.compile(r"https?://[^\s)>\]`'\"]+")),
)
_PUBLIC_HOST_RE = re.compile(
    r"^(?:[\w-]+\.)*(?:github\.com|gitlab\.com|apple\.com|developer\.apple\.com|microsoft\.com|"
    r"learn\.microsoft\.com|docs\.rs|crates\.io|pypi\.org|npmjs\.com|python\.org|rust-lang\.org|"
    r"wikipedia\.org|w3\.org|ietf\.org|mozilla\.org|google\.com|example\.com|example\.org)$"
)
_PRIVATE_HOST_RE = re.compile(
    r"(?:^localhost$|^\d{1,3}(?:\.\d{1,3}){3}$|\.(?:local|internal|lan|corp|intranet)$|^gitlab\.|"
    r"^git\.|^intranet\.|^jira\.|^confluence\.)"
)
_TEXT_SUFFIXES = (
    ".md",
    ".sh",
    ".ps1",
    ".py",
    ".rb",
    ".js",
    ".ts",
    ".swift",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
    ".toml",
    ".plist",
)


@dataclass(frozen=True)
class Suspect:
    """A line that looks project-specific: `file:line  kind: what`."""

    file: str
    line: int
    kind: str
    text: str

    def format(self) -> str:
        return f"{self.file}:{self.line}  {self.kind}: {self.text}"


@dataclass(frozen=True)
class ExportedSkill:
    """What `generalise_skill` produces — files for `skills/<name>/`, not side effects."""

    name: str
    # `SKILL.md`, `tools/<tool>/TOOL.md`, `tools/<tool>/reference.<ext>`, fixtures.
    files: dict[str, bytes]
    tools: tuple[str, ...]
    suspects: tuple[Suspect, ...]
    placeholders: tuple[str, ...]


def referenced_tools(markdown: str) -> tuple[str, ...]:
    """Tools an expanded skill links to (`../../tools/<name>/TOOL.md`), in order."""
    seen: list[str] = []
    for match in _TOOL_REF_RE.finditer(markdown):
        name = match.group("name")
        if name not in seen:
            seen.append(name)
    return tuple(seen)


def strip_project_section(body: str) -> str:
    """Everything above `## In this project` — the part that was, or becomes, upstream."""
    if body.lstrip("\n").startswith(PROJECT_HEADING):
        return ""
    index = body.find(f"\n{PROJECT_HEADING}")
    return body if index < 0 else body[:index]


def generalise_skill(
    markdown: str,
    *,
    version: str,
    scope: str | None,
    tools: dict[str, dict[str, bytes]],
    uses: tuple[str, ...] = (),
    platform: str | None = None,
) -> ExportedSkill:
    """Turn an expanded project skill back into a library bundle.

    `tools` maps each tool name to the files in `.agent/tools/<name>/`
    (relative name → bytes). `platform` says which implementation becomes
    `reference.<ext>` when several exist (default: the first of `PLATFORMS`).
    """
    skill = parse_skill(markdown)
    body = strip_project_section(skill.body).strip("\n") + "\n"
    body = _PROJECT_TOOLS_LINK_RE.sub("](tools/", body)
    text = f"---\n{_frontmatter(skill, version=version, scope=scope, uses=uses)}---\n\n{body}"
    files: dict[str, bytes] = {SKILL_FILENAME: text.encode("utf-8")}
    for name, tool_files in sorted(tools.items()):
        reference = _pick_reference(tool_files, platform)
        for filename, data in sorted(tool_files.items()):
            stem, _, ext = filename.partition(".")
            if stem in PLATFORMS:
                if filename == reference:
                    files[f"{TOOLS_DIR}/{name}/{REFERENCE_STEM}.{ext}"] = data
                continue  # other platforms' implementations were written here and stay here
            files[f"{TOOLS_DIR}/{name}/{filename}"] = data
    return ExportedSkill(
        name=skill.name,
        files=files,
        tools=tuple(sorted(tools)),
        suspects=find_suspects(files),
        placeholders=tuple(find_placeholders(body)),
    )


def find_suspects(files: dict[str, bytes]) -> tuple[Suspect, ...]:
    """Lines in text files that look like they belong to one project, not to everyone."""
    found: list[Suspect] = []
    for path in sorted(files):
        if not path.endswith(_TEXT_SUFFIXES):
            continue
        text = files[path].decode("utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in _SUSPECT_PATTERNS:
                for match in pattern.finditer(line):
                    hit = match.group(0).rstrip(".,;")
                    if kind == "host" and not _private_host(hit):
                        continue
                    if kind == "path" and _is_placeholder_only(hit):
                        continue
                    suspect = Suspect(file=path, line=number, kind=kind, text=hit)
                    if suspect not in found:
                        found.append(suspect)
    return tuple(found)


def _private_host(url: str) -> bool:
    host = re.sub(r"^https?://", "", url).split("/", 1)[0]
    host, _, port = host.partition(":")
    if _PUBLIC_HOST_RE.match(host):
        return False
    return bool(port) or bool(_PRIVATE_HOST_RE.search(host))


def _is_placeholder_only(hit: str) -> bool:
    """`~/` alone, or a path whose first real segment is already a placeholder."""
    return hit == "~/" or "<" in hit


def _pick_reference(tool_files: dict[str, bytes], platform: str | None) -> str | None:
    if any(name.partition(".")[0] == REFERENCE_STEM for name in tool_files):
        return None  # a reference travelled in with the skill; keep that one
    order = (platform, *PLATFORMS) if platform else PLATFORMS
    for candidate in order:
        for name in sorted(tool_files):
            if name.partition(".")[0] == candidate:
                return name
    return None


def _frontmatter(skill: Skill, *, version: str, scope: str | None, uses: tuple[str, ...]) -> str:
    front: dict[str, Any] = {"name": skill.name, "description": skill.description}
    if skill.license:
        front["license"] = skill.license
    if skill.compatibility:
        front["compatibility"] = skill.compatibility
    if skill.allowed_tools:
        front["allowed-tools"] = skill.allowed_tools
    metadata: dict[str, str] = {f"{META_PREFIX}version": version}
    if scope:
        metadata[f"{META_PREFIX}scope"] = scope
    if uses:
        metadata[f"{META_PREFIX}uses"] = ", ".join(uses)
    for key, value in skill.metadata.items():
        if not key.startswith(META_PREFIX):
            metadata[key] = value
    front["metadata"] = metadata
    return yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=88)


__all__ = [
    "REFERENCE_STEM",
    "ExportedSkill",
    "Suspect",
    "find_suspects",
    "generalise_skill",
    "referenced_tools",
    "strip_project_section",
]
