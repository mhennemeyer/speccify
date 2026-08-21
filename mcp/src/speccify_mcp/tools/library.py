"""Reading playbooks: list them, read one, read a single step.

This is the main path in the new model — an agent asks for the knowledge, not
for files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LibraryResult:
    ok: bool
    playbooks: list[dict[str, Any]] = field(default_factory=list)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "playbooks": list(self.playbooks),
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True)
class PlaybookResult:
    ok: bool
    playbook: dict[str, Any] = field(default_factory=dict)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "playbook": dict(self.playbook),
            "code": self.code,
            "message": self.message,
        }


def run_skill_list(project_root: Path, *, library_path: Path | None = None) -> LibraryResult:
    """Every skill available to this project.

    Deliberately shallow: name, description and the axes. The description is
    what decides whether a skill is the right one, and the body costs context
    that this call should not spend for nine skills the agent will not use.
    """
    from speccify_cli.commands._context import ProjectContext
    from speccify_core import LibraryError
    from speccify_core.skill_library import LocalSkillLibrary

    try:
        if library_path is not None:
            root = library_path if library_path.is_absolute() else project_root / library_path
        else:
            root = ProjectContext.load(project_root).manifest.resolved_library_path()
        if not root.is_dir():
            return LibraryResult(ok=True, playbooks=[])
        library = LocalSkillLibrary(root)
        skills = []
        for skill_id, version in library.list_playbooks():
            skill = library.fetch(skill_id, version).skill()
            skills.append(
                {
                    "id": skill.qualified_id,
                    "name": skill.name,
                    "version": skill.version,
                    "description": skill.description,
                    "stack": list(skill.stack),
                    "platforms": list(skill.platforms),
                    "uses": list(skill.uses),
                    "deprecated": skill.deprecated,
                }
            )
        return LibraryResult(ok=True, playbooks=skills)
    except (LibraryError, FileNotFoundError, ValueError) as exc:
        return LibraryResult(ok=False, code="library_unavailable", message=str(exc))


def run_skill_get(
    project_root: Path,
    *,
    reference: str,
    library_path: Path | None = None,
    offline: bool = False,
) -> PlaybookResult:
    """A whole skill — body included. For inspecting one that is not installed."""
    from speccify_cli.commands.show import run_show
    from speccify_core import LibraryError

    try:
        data = run_show(
            project_root,
            reference,
            library_override=library_path,
            offline=offline,
        )
    except (LibraryError, FileNotFoundError, ValueError) as exc:
        return PlaybookResult(ok=False, code="not_found", message=str(exc))
    return PlaybookResult(ok=True, playbook=data)


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    tool: dict[str, Any] = field(default_factory=dict)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "tool": dict(self.tool), "code": self.code, "message": self.message}


def run_tool_get(
    project_root: Path,
    *,
    reference: str,
    tool: str,
    library_path: Path | None = None,
    offline: bool = False,
) -> ToolResult:
    """The full contract of one tool spec — schemas, effects, examples, body.

    This is what an agent reads before it writes the implementation for the
    machine it is on. The spec travels; the script would not have.
    """
    from speccify_cli.commands._context import ProjectContext, fetch_bundle, list_versions
    from speccify_cli.commands.show import tool_as_dict
    from speccify_core import LibraryError, parse_uses_entry
    from speccify_core.skill_check import tools_from_bundle
    from speccify_core.tool import Tool

    try:
        context = ProjectContext.load(project_root, library_override=library_path, offline=offline)
        skill_id, _ = parse_uses_entry(reference)
        versions = list_versions(context.libraries, skill_id)
        if not versions:
            raise LibraryError(f"'{skill_id}' is not available.")
        bundle = fetch_bundle(context.libraries, skill_id, versions[-1])
        specs = tools_from_bundle(bundle.files)
        spec = specs.get(tool)
        if not isinstance(spec, Tool):
            available = ", ".join(sorted(specs)) or "none"
            raise LibraryError(f"'{skill_id}' has no tool '{tool}'. Available: {available}.")
    except (LibraryError, FileNotFoundError, ValueError) as exc:
        return ToolResult(ok=False, code="not_found", message=str(exc))

    prefix = f"tools/{tool}/"
    files = sorted(
        path[len(prefix) :]
        for path in bundle.files
        if path.startswith(prefix) and path != f"{prefix}TOOL.md"
    )
    return ToolResult(ok=True, tool=tool_as_dict(spec, files=files))


@dataclass(frozen=True)
class AssetResult:
    ok: bool
    path: str = ""
    encoding: str = ""
    content: str = ""
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "path": self.path,
            "encoding": self.encoding,
            "content": self.content,
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    findings: list[dict[str, Any]] = field(default_factory=list)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "findings": list(self.findings),
            "code": self.code,
            "message": self.message,
        }


def run_skill_asset(
    project_root: Path,
    *,
    reference: str,
    path: str,
    library_path: Path | None = None,
    offline: bool = False,
) -> AssetResult:
    """The content of one asset — text when it decodes, base64 otherwise."""
    import base64

    from speccify_cli.commands._context import ProjectContext, fetch_bundle, list_versions
    from speccify_core import LibraryError, parse_uses_entry

    try:
        context = ProjectContext.load(project_root, library_override=library_path, offline=offline)
        skill_id, _ = parse_uses_entry(reference)
        versions = list_versions(context.libraries, skill_id)
        if not versions:
            raise LibraryError(f"'{skill_id}' is not available.")
        bundle = fetch_bundle(context.libraries, skill_id, versions[-1])
        data = bundle.files.get(path)
        if data is None:
            available = ", ".join(sorted(p for p in bundle.files if p != "SKILL.md")) or "none"
            raise LibraryError(f"'{path}' is not in this bundle. Available: {available}.")
    except (LibraryError, FileNotFoundError, ValueError) as exc:
        return AssetResult(ok=False, code="not_found", message=str(exc))

    try:
        return AssetResult(ok=True, path=path, encoding="utf-8", content=data.decode("utf-8"))
    except UnicodeDecodeError:
        return AssetResult(
            ok=True,
            path=path,
            encoding="base64",
            content=base64.b64encode(data).decode("ascii"),
        )


def run_skill_check(
    project_root: Path,
    *,
    reference: str,
    links: bool = False,
    library_path: Path | None = None,
    offline: bool = False,
) -> CheckResult:
    """Is this skill still current and well made? Spec, best practice, source age."""
    from speccify_cli.commands._context import ProjectContext, fetch_bundle, list_versions
    from speccify_core import LibraryError, check_links, parse_uses_entry
    from speccify_core.skill_check import check_skill

    try:
        context = ProjectContext.load(project_root, library_override=library_path, offline=offline)
        skill_id, _ = parse_uses_entry(reference)
        versions = list_versions(context.libraries, skill_id)
        if not versions:
            raise LibraryError(f"'{skill_id}' is not available.")
        bundle = fetch_bundle(context.libraries, skill_id, versions[-1])
        if not bundle.is_skill:
            raise LibraryError(f"'{skill_id}' is not a skill — the bundle has no SKILL.md.")
        skill = bundle.skill()
    except (LibraryError, FileNotFoundError, ValueError) as exc:
        return CheckResult(ok=False, code="not_found", message=str(exc))

    findings = check_skill(skill, bundle_files=set(bundle.files))
    if links and not any(finding.is_error for finding in findings):
        findings.extend(check_links(skill.sources))
    return CheckResult(
        ok=not any(finding.is_error for finding in findings),
        findings=[{"level": f.level, "path": f.path, "message": f.message} for f in findings],
    )
