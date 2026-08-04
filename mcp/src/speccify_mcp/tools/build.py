"""`build`-Tool: komplettes Projekt aus einer `kind: app`-Spec (Phase P4).

Dünner Adapter über `speccify_cli.commands.build.run_build` (Single Source of
Truth, gleiches Muster wie `mock`). Schreibt das Projekt nach `out_dir` und
gibt die Pfade + Template-Pin strukturiert zurück; Fehler sind strukturierte
Antworten, keine MCP-Errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BuildResult:
    """Strukturiertes Ergebnis des `build`-Tools."""

    ok: bool
    files: list[str] = field(default_factory=list)
    out_dir: str = ""
    template_set: str = ""
    template_version: str = ""
    mocks: bool = True
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "files": list(self.files),
            "out_dir": self.out_dir,
            "template_set": self.template_set,
            "template_version": self.template_version,
            "mocks": self.mocks,
            "code": self.code,
            "message": self.message,
        }


def run_build(
    project_root: Path,
    *,
    spec_ref: str,
    out_dir: Path,
    registry_path: Path | None = None,
    target: str = "react",
    mocks: bool = True,
    offline: bool = True,
    cache_dir: Path | None = None,
) -> BuildResult:
    """Baut das Projekt für `spec_ref` nach `out_dir` (relativ zum Projekt)."""
    from speccify_cli.commands._llm_client import build_replay_client
    from speccify_cli.commands.build import run_build as cli_run_build
    from speccify_core import CacheMissError, RegistryError
    from speccify_core.codegen.app_react import AppCodegenError

    resolved_registry = (
        registry_path if registry_path is not None else project_root / "registry-fixtures"
    )
    resolved_out = out_dir if out_dir.is_absolute() else project_root / out_dir
    resolved_cache = (
        cache_dir if cache_dir is None or cache_dir.is_absolute() else (project_root / cache_dir)
    )
    try:
        client = None if mocks else build_replay_client(cache_dir=resolved_cache, offline=offline)
        result = cli_run_build(
            spec_ref,
            registry_path=resolved_registry,
            out_dir=resolved_out,
            target=target,
            mocks=mocks,
            llm_client=client,
        )
    except CacheMissError as exc:
        return BuildResult(ok=False, code="cache_miss", message=str(exc))
    except (AppCodegenError, RegistryError, ValueError) as exc:
        return BuildResult(ok=False, code="build_failed", message=str(exc))
    return BuildResult(
        ok=True,
        files=sorted(result.files),
        out_dir=str(resolved_out),
        template_set=result.template_set,
        template_version=result.template_version,
        mocks=result.mocks,
    )
