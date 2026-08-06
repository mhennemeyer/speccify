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


def run_playbook_list(project_root: Path, *, library_path: Path | None = None) -> LibraryResult:
    """Every playbook available to this project."""
    from speccify_cli.commands._context import ProjectContext
    from speccify_core import LibraryError, LocalLibrary, parse_playbook

    try:
        if library_path is not None:
            root = library_path if library_path.is_absolute() else project_root / library_path
        else:
            root = ProjectContext.load(project_root).manifest.resolved_library_path()
        if not root.is_dir():
            return LibraryResult(ok=True, playbooks=[])
        library = LocalLibrary(root)
        playbooks = []
        for playbook_id, version in library.list_playbooks():
            bundle = library.fetch(playbook_id, version)
            parsed = parse_playbook(bundle.parsed())
            playbooks.append(
                {
                    "id": parsed.id,
                    "version": parsed.version,
                    "title": parsed.title,
                    "summary": parsed.summary,
                    "keywords": list(parsed.applies_to.keywords),
                    "platforms": list(parsed.applies_to.platforms),
                    "steps": len(parsed.steps),
                }
            )
        return LibraryResult(ok=True, playbooks=playbooks)
    except (LibraryError, FileNotFoundError, ValueError) as exc:
        return LibraryResult(ok=False, code="library_unavailable", message=str(exc))


def run_playbook_get(
    project_root: Path,
    *,
    reference: str,
    library_path: Path | None = None,
    offline: bool = False,
) -> PlaybookResult:
    """A whole playbook: steps, resolved sources, pitfalls, asset list."""
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


def run_playbook_step(
    project_root: Path,
    *,
    reference: str,
    step_id: str,
    library_path: Path | None = None,
    offline: bool = False,
) -> PlaybookResult:
    """One step with its sources resolved — the unit an agent works through."""
    from speccify_cli.commands.show import run_show
    from speccify_core import LibraryError

    try:
        data = run_show(
            project_root,
            reference,
            step_id=step_id,
            library_override=library_path,
            offline=offline,
        )
    except (LibraryError, FileNotFoundError, ValueError) as exc:
        return PlaybookResult(ok=False, code="not_found", message=str(exc))
    return PlaybookResult(ok=True, playbook=data)


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


def run_playbook_asset(
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
        playbook_id, _ = parse_uses_entry(reference)
        versions = list_versions(context.libraries, playbook_id)
        if not versions:
            raise LibraryError(f"'{playbook_id}' is not available.")
        bundle = fetch_bundle(context.libraries, playbook_id, versions[-1])
        data = bundle.files.get(path)
        if data is None:
            available = ", ".join(bundle.asset_paths) or "none"
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


def run_playbook_check(
    project_root: Path,
    *,
    reference: str,
    links: bool = False,
    library_path: Path | None = None,
    offline: bool = False,
) -> CheckResult:
    """Is this playbook still current? Structure, source age, optionally links."""
    from speccify_cli.commands._context import ProjectContext, fetch_bundle, list_versions
    from speccify_core import (
        LibraryError,
        check_links,
        check_playbook,
        parse_playbook,
        parse_uses_entry,
    )

    try:
        context = ProjectContext.load(project_root, library_override=library_path, offline=offline)
        playbook_id, _ = parse_uses_entry(reference)
        versions = list_versions(context.libraries, playbook_id)
        if not versions:
            raise LibraryError(f"'{playbook_id}' is not available.")
        bundle = fetch_bundle(context.libraries, playbook_id, versions[-1])
    except (LibraryError, FileNotFoundError, ValueError) as exc:
        return CheckResult(ok=False, code="not_found", message=str(exc))

    findings = check_playbook(bundle.parsed(), bundle_files=set(bundle.files))
    if links and not any(finding.is_error for finding in findings):
        findings.extend(check_links(parse_playbook(bundle.parsed())))
    return CheckResult(
        ok=not any(finding.is_error for finding in findings),
        findings=[{"level": f.level, "path": f.path, "message": f.message} for f in findings],
    )
