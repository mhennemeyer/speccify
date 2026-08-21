"""Project-level tools: lock, pull, expand, verify, tool_check — thin adapters over the CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProjectResult:
    ok: bool
    entries: list[dict[str, Any]] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "entries": list(self.entries),
            "files": list(self.files),
            "problems": list(self.problems),
            "code": self.code,
            "message": self.message,
        }


def run_lock(project_root: Path, *, library_path: Path | None = None) -> ProjectResult:
    from speccify_cli.commands.lock import run_lock as cli_lock
    from speccify_core import LibraryError, LockfileError, ManifestError, ResolverError

    try:
        lockfile = cli_lock(project_root, library_path)
    except (ResolverError, LibraryError, LockfileError, ManifestError, FileNotFoundError) as exc:
        return ProjectResult(ok=False, code="lock_failed", message=str(exc))
    return ProjectResult(
        ok=True,
        entries=[
            {
                "id": entry.id,
                "version": entry.version,
                "resolved_via": entry.resolved_via,
                "source_commit": entry.source_commit,
                "bundle_sha256": entry.bundle_sha256,
            }
            for entry in lockfile.entries
        ],
    )


def run_pull(
    project_root: Path,
    *,
    out_dir: Path,
    library_path: Path | None = None,
    offline: bool = False,
) -> ProjectResult:
    from speccify_cli.commands.pull import run_pull as cli_pull
    from speccify_core import LibraryError, LockfileError

    resolved_out = out_dir if out_dir.is_absolute() else project_root / out_dir
    try:
        written = cli_pull(
            project_root, resolved_out, library_override=library_path, offline=offline
        )
    except (LockfileError, LibraryError, FileNotFoundError) as exc:
        return ProjectResult(ok=False, code="pull_failed", message=str(exc))
    return ProjectResult(ok=True, files=[str(path) for path in written])


@dataclass(frozen=True)
class ExpandResult:
    ok: bool
    platform: str = ""
    skills: list[dict[str, Any]] = field(default_factory=list)
    tools_to_implement: list[str] = field(default_factory=list)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "platform": self.platform,
            "skills": list(self.skills),
            "tools_to_implement": list(self.tools_to_implement),
            "code": self.code,
            "message": self.message,
        }


def run_expand(
    project_root: Path,
    *,
    references: list[str] | None = None,
    library_path: Path | None = None,
    offline: bool = False,
    platform: str | None = None,
) -> ExpandResult:
    """Make normal, project-specific skills under `.agent/` and say what is left to do."""
    from speccify_cli.commands.expand import run_expand as cli_expand
    from speccify_core import LibraryError, LockfileError

    try:
        report = cli_expand(
            project_root,
            references or None,
            library_override=library_path,
            offline=offline,
            platform=platform,
        )
    except (LockfileError, LibraryError, FileNotFoundError, ValueError) as exc:
        return ExpandResult(ok=False, code="expand_failed", message=str(exc))
    return ExpandResult(
        ok=True,
        platform=report.platform,
        skills=[
            {
                "name": o.name,
                "action": o.action,
                "path": f".agent/skills/{o.name}",
                "used_by": o.via,
                "placeholders": list(o.placeholders),
                "tools_to_implement": list(o.tools_to_implement),
            }
            for o in report.outcomes
        ],
        tools_to_implement=report.tools_to_implement,
    )


def run_verify(
    project_root: Path,
    *,
    library_path: Path | None = None,
    offline: bool = False,
) -> ProjectResult:
    from speccify_cli.commands.verify import run_verify as cli_verify
    from speccify_core import LockfileError

    try:
        problems = cli_verify(project_root, library_override=library_path, offline=offline)
    except (LockfileError, FileNotFoundError) as exc:
        return ProjectResult(ok=False, code="verify_failed", message=str(exc))
    return ProjectResult(ok=not problems, problems=problems)


@dataclass(frozen=True)
class ToolCheckResult:
    ok: bool
    platform: str = ""
    tools: list[dict[str, Any]] = field(default_factory=list)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "platform": self.platform,
            "tools": list(self.tools),
            "code": self.code,
            "message": self.message,
        }


def run_tool_check(
    project_root: Path,
    *,
    names: list[str] | None = None,
    platform: str | None = None,
    timeout: float | None = None,
) -> ToolCheckResult:
    """Run each tool spec's examples against this platform's implementation."""
    from speccify_cli.commands.tool import run_tool_check as cli_tool_check
    from speccify_core.tool_check import DEFAULT_TIMEOUT

    try:
        report = cli_tool_check(
            project_root,
            names or None,
            platform=platform,
            timeout=DEFAULT_TIMEOUT if timeout is None else timeout,
        )
    except (FileNotFoundError, ValueError) as exc:
        return ToolCheckResult(ok=False, code="tool_check_failed", message=str(exc))
    return ToolCheckResult(
        ok=report.ok,
        platform=report.platform,
        tools=[r.to_dict() for r in report.results],
    )
