"""Expand: turn a skill from a source repository into a normal skill in a project.

Two forms of a skill exist, and this module is the transition between them:

* **In the source** a skill carries `metadata.speccify.*`, refers to other
  skills through `speccify.uses`, and *specifies* its tools in
  `tools/<name>/TOOL.md`.
* **In the project** (`.agent/skills/<name>/`) it is a plain skill — the
  Markdown an agent reads, nothing Speccify-specific left in it. References
  are resolved to sibling skills, the Speccify metadata is gone, the tool
  specs live project-wide under `.agent/tools/<name>/` (two skills can share
  one implementation), and everything specific to this project is *appended*
  under one heading, never mixed into the upstream text.

That last rule is what keeps re-expansion cheap: when upstream changes, the
upstream part is regenerated and the project section is carried over as it
was. No three-way merge, because the two never overlap.

Provenance does not live in the skill — it lives in `expansions.yaml`, so the
skill stays normal and Speccify still knows where it came from, which upstream
hash it was made from, and which tools have an implementation for which
platform.
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from speccify_core.skill import META_PREFIX, SKILL_FILENAME, Skill
from speccify_core.tool import TOOL_FILENAME, TOOLS_DIR

PROJECT_HEADING = "## In this project"
AGENT_DIR = ".agent"
SKILLS_DIR = "skills"
EXPANSIONS_FILENAME = "expansions.yaml"
CURRENT_EXPANSIONS_SCHEMA_VERSION = 1

# Tool implementation status, per platform.
SPECIFIED = "specified"
IMPLEMENTED = "implemented"
VERIFIED = "verified"

PLATFORMS = ("macos", "linux", "windows")

# `<bundle-id>`, `<path to .app>`, `<vendor-dir>` — things the author left for
# the reader to fill in. Not HTML, not autolinks: no `/`, no `:`, no `=`.
_PLACEHOLDER_RE = re.compile(r"<(?P<text>[a-z][a-z0-9 ._-]{1,40})>")
_HTML_TAGS = frozenset(
    {"br", "p", "a", "b", "i", "em", "strong", "code", "pre", "div", "span", "hr", "ul", "li"}
)
_SHOUT_RE = re.compile(r"\b(?:YOUR_[A-Z_]+|TODO|TBD|CHANGEME)\b")
# Links into the skill's own `tools/` directory move two levels up.
_TOOLS_LINK_RE = re.compile(r"\]\((?:\./)?tools/")


def current_platform() -> str:
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


@dataclass(frozen=True)
class ExpandedSkill:
    """What `expand_skill` produces for one skill — files, not side effects."""

    name: str
    skill_markdown: str
    # `tools/<name>/<file>` → bytes, to be written under `.agent/tools/`.
    tool_files: dict[str, bytes]
    tool_names: tuple[str, ...]
    uses: tuple[str, ...]
    placeholders: tuple[str, ...]


def expand_skill(
    skill: Skill,
    files: dict[str, bytes],
    *,
    sibling_names: dict[str, str],
    existing_markdown: str | None = None,
) -> ExpandedSkill:
    """Normalise one skill.

    `sibling_names` maps each `uses` reference to the directory name it will
    have next to this skill — the caller knows, because it expands them too.
    `existing_markdown` is the previously expanded file, if any; its project
    section is carried over unchanged.
    """
    tool_names = tuple(sorted(_tool_names(files)))
    body = _TOOLS_LINK_RE.sub("](../../tools/", skill.body).strip("\n") + "\n"
    project = _project_section(existing_markdown) or _fresh_project_section(
        skill, tool_names=tool_names, sibling_names=sibling_names
    )
    markdown = f"---\n{_frontmatter(skill)}---\n\n{body}\n{project}"
    tool_files = {path: data for path, data in files.items() if path.startswith(f"{TOOLS_DIR}/")}
    return ExpandedSkill(
        name=skill.name,
        skill_markdown=markdown,
        tool_files=tool_files,
        tool_names=tool_names,
        uses=skill.uses,
        placeholders=tuple(find_placeholders(skill.body)),
    )


def find_placeholders(body: str) -> list[str]:
    """Distinct things the author left for the reader to fill in, in order."""
    seen: list[str] = []
    for match in _PLACEHOLDER_RE.finditer(body):
        text = match.group("text")
        # Known HTML, autolinks, and anything that is closed again later — a
        # plist's `<key>…</key>` is markup, not a blank to fill.
        if text in _HTML_TAGS or text.startswith("http") or f"</{text}>" in body:
            continue
        token = f"<{text}>"
        if token not in seen:
            seen.append(token)
    for match in _SHOUT_RE.finditer(body):
        if match.group(0) not in seen:
            seen.append(match.group(0))
    return seen


def _tool_names(files: dict[str, bytes]) -> list[str]:
    names = []
    for path in files:
        parts = path.split("/")
        if len(parts) == 3 and parts[0] == TOOLS_DIR and parts[2] == TOOL_FILENAME:
            names.append(parts[1])
    return names


def _frontmatter(skill: Skill) -> str:
    """The spec's fields, minus everything `speccify.*`."""
    front: dict[str, Any] = {"name": skill.name, "description": skill.description}
    if skill.license:
        front["license"] = skill.license
    if skill.compatibility:
        front["compatibility"] = skill.compatibility
    if skill.allowed_tools:
        front["allowed-tools"] = skill.allowed_tools
    metadata = {k: v for k, v in skill.metadata.items() if not k.startswith(META_PREFIX)}
    if metadata:
        front["metadata"] = metadata
    return yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=88)


def _project_section(markdown: str | None) -> str | None:
    if not markdown:
        return None
    index = markdown.find(f"\n{PROJECT_HEADING}")
    if index < 0:
        return None
    return markdown[index + 1 :].rstrip() + "\n"


def _fresh_project_section(
    skill: Skill, *, tool_names: tuple[str, ...], sibling_names: dict[str, str]
) -> str:
    lines = [
        PROJECT_HEADING,
        "",
        "<!-- Everything above is upstream and is replaced on re-expand; this",
        "     section is yours and is kept. Fill in what is specific here. -->",
        "",
    ]
    for used in skill.uses:
        name = sibling_names.get(used, used.rsplit("/", 1)[-1].split("@", 1)[0])
        lines.append(f"- Builds on [{name}](../{name}/{SKILL_FILENAME}).")
    for tool in tool_names:
        lines.append(
            f"- Tool [{tool}](../../tools/{tool}/{TOOL_FILENAME}) — implemented for this "
            f"platform in `.agent/tools/{tool}/`; see the examples there for the contract."
        )
    if len(lines) == 5:
        lines.append("- _Nothing project-specific yet._")
    return "\n".join(lines) + "\n"


# --- Provenance ---------------------------------------------------------------------


@dataclass(frozen=True)
class ToolRecord:
    """One tool in the project: which skills brought it, and where it stands per platform."""

    from_skills: tuple[str, ...]
    spec_sha256: str
    platforms: dict[str, dict[str, str]] = field(default_factory=dict)

    def status(self, platform: str) -> str:
        return self.platforms.get(platform, {}).get("status", SPECIFIED)


@dataclass(frozen=True)
class SkillRecord:
    source: str
    version: str
    bundle_sha256: str
    expanded: str
    requested: bool
    tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class Expansions:
    skills: dict[str, SkillRecord] = field(default_factory=dict)
    tools: dict[str, ToolRecord] = field(default_factory=dict)
    schema_version: int = CURRENT_EXPANSIONS_SCHEMA_VERSION

    @classmethod
    def load(cls, path: Path) -> Expansions:
        if not path.is_file():
            return cls()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        skills = {
            name: SkillRecord(
                source=str(s["source"]),
                version=str(s["version"]),
                bundle_sha256=str(s["bundle_sha256"]),
                expanded=str(s["expanded"]),
                requested=bool(s.get("requested", True)),
                tools=tuple(s.get("tools") or ()),
            )
            for name, s in (data.get("skills") or {}).items()
        }
        tools = {
            name: ToolRecord(
                from_skills=tuple(t.get("from") or ()),
                spec_sha256=str(t["spec_sha256"]),
                platforms={
                    str(p): {str(k): str(v) for k, v in (info or {}).items()}
                    for p, info in (t.get("platforms") or {}).items()
                },
            )
            for name, t in (data.get("tools") or {}).items()
        }
        return cls(skills=skills, tools=tools, schema_version=int(data.get("schema_version", 1)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "skills": {
                name: {
                    "source": s.source,
                    "version": s.version,
                    "bundle_sha256": s.bundle_sha256,
                    "expanded": s.expanded,
                    "requested": s.requested,
                    "tools": list(s.tools),
                }
                for name, s in sorted(self.skills.items())
            },
            "tools": {
                name: {
                    "from": list(t.from_skills),
                    "spec_sha256": t.spec_sha256,
                    "platforms": {p: dict(info) for p, info in sorted(t.platforms.items())},
                }
                for name, t in sorted(self.tools.items())
            },
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "# Written by `speccify expand`. Where each skill under .agent/skills/ came\n"
            "# from, and which tools under .agent/tools/ are implemented for which\n"
            "# platform. Edit the skills, not this file.\n"
        )
        path.write_text(
            header + yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def sha256_text(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def implementation_for(tool_dir: Path, platform: str) -> Path | None:
    """The implementation file for a platform: `<platform>.<anything>`, e.g. `macos.sh`."""
    if not tool_dir.is_dir():
        return None
    matches = sorted(
        p for p in tool_dir.iterdir() if p.is_file() and p.stem == platform and p.suffix
    )
    return matches[0] if matches else None


__all__ = [
    "AGENT_DIR",
    "CURRENT_EXPANSIONS_SCHEMA_VERSION",
    "EXPANSIONS_FILENAME",
    "IMPLEMENTED",
    "PLATFORMS",
    "PROJECT_HEADING",
    "SKILLS_DIR",
    "SPECIFIED",
    "VERIFIED",
    "ExpandedSkill",
    "Expansions",
    "SkillRecord",
    "ToolRecord",
    "current_platform",
    "expand_skill",
    "find_placeholders",
    "implementation_for",
    "sha256_text",
]
