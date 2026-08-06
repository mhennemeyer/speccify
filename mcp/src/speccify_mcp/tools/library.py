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
