"""`mock`-Tool: deterministische Mock-Komponenten aus dem API-Vertrag (P2 Stage 5).

Dünner Adapter über `speccify_cli.commands.mock.run_mock` (Single Source of
Truth, gleiches Muster wie `lock`/`pull`/`verify`). Schreibt die Mock-Dateien
nach `out_dir` und gibt die Pfade + den Template-Pin strukturiert zurück.
`mock_unavailable` (z. B. logic-Spec ohne Fixtures) ist eine strukturierte
Antwort, kein MCP-Error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MockResult:
    """Strukturiertes Ergebnis des `mock`-Tools."""

    ok: bool
    files: list[str] = field(default_factory=list)
    out_dir: str = ""
    template_set: str = ""
    template_version: str = ""
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "files": list(self.files),
            "out_dir": self.out_dir,
            "template_set": self.template_set,
            "template_version": self.template_version,
            "code": self.code,
            "message": self.message,
        }


def run_mock(
    project_root: Path,
    *,
    spec_ref: str,
    out_dir: Path,
    registry_path: Path | None = None,
    target: str = "react",
) -> MockResult:
    """Rendert die Mock-Closure für `spec_ref` nach `out_dir` (relativ zum Projekt)."""
    from speccify_cli.commands.mock import run_mock as cli_run_mock
    from speccify_core import MockCodegenError, MockUnavailableError, RegistryError

    resolved_registry = (
        registry_path if registry_path is not None else project_root / "registry-fixtures"
    )
    resolved_out = out_dir if out_dir.is_absolute() else project_root / out_dir
    try:
        result = cli_run_mock(
            spec_ref,
            registry_path=resolved_registry,
            out_dir=resolved_out,
            target=target,
        )
    except MockUnavailableError as exc:
        return MockResult(ok=False, code="mock_unavailable", message=str(exc))
    except (MockCodegenError, RegistryError, ValueError) as exc:
        return MockResult(ok=False, code="mock_failed", message=str(exc))
    return MockResult(
        ok=True,
        files=sorted(result.files),
        out_dir=str(resolved_out),
        template_set=result.template_set,
        template_version=result.template_version,
    )
