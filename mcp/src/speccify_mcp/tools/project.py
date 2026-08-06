"""Project-level tools: lock, pull, verify — thin adapters over the CLI."""

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
