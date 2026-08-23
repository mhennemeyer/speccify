"""Quellen: was ein Skills-Repo anbietet, und eine Abhängigkeit hinzufügen.

Das ist der Weg, über den eine App (iKanban AI) ein Repo „einbindet": erst
`source_list` (was gibt es dort?), dann `add` (ins Manifest + Lock), dann
`expand`. Beides dünne Adapter — `add` ruft den CLI-Befehl, `source_list` die
Core-Bibliothek — damit CLI und MCP nicht auseinanderlaufen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SourceResult:
    ok: bool
    source: str = ""
    skills: list[dict[str, Any]] = field(default_factory=list)
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "source": self.source,
            "skills": list(self.skills),
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True)
class AddResult:
    ok: bool
    reference: str = ""
    range: str = ""
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reference": self.reference,
            "range": self.range,
            "code": self.code,
            "message": self.message,
        }


def run_source_list(source: str, *, offline: bool = False) -> SourceResult:
    """Alle Bundles, die ein Git-Repo laut seinen Tags anbietet."""
    from speccify_core import GitLibrary, GitLibraryError, is_git_ref

    if not is_git_ref(source):
        return SourceResult(
            ok=False,
            source=source,
            code="not_a_git_source",
            message=f"'{source}' ist keine Git-Quelle — erwartet 'git+<url>'.",
        )
    try:
        listings = GitLibrary(offline=offline).list_bundles(source)
    except GitLibraryError as exc:
        return SourceResult(ok=False, source=source, code="source_unreachable", message=str(exc))
    return SourceResult(ok=True, source=source, skills=[b.to_dict() for b in listings])


def run_add(project_root: Path, *, reference: str, library_path: Path | None = None) -> AddResult:
    """`speccify add`: Abhängigkeit ins Manifest, Lockfile neu schreiben."""
    from speccify_cli.commands.add import run_add as cli_add
    from speccify_core import LibraryError, ManifestError, RegistryError, ResolverError

    try:
        range_raw = cli_add(project_root, reference, library_path)
    except (
        ResolverError,
        RegistryError,
        LibraryError,
        ManifestError,
        FileNotFoundError,
        ValueError,
    ) as exc:
        return AddResult(ok=False, reference=reference, code="add_failed", message=str(exc))
    return AddResult(ok=True, reference=reference, range=range_raw)
