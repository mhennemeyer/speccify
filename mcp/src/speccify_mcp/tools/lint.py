"""`lint`-Tool: validiert eine einzelne YAML-Spec gegen das Spec-Schema v0.

Spiegelt `speccify lint <file>` — Output ist ein strukturiertes Dict mit
`ok: bool`, `skipped: bool` (Projekt-Manifeste ohne `kind` werden wie in
der CLI übersprungen) und `issues: list[{path, message}]`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from speccify_core import SchemaValidator, SpecLoader


@dataclass(frozen=True)
class LintResult:
    spec_path: str
    ok: bool
    skipped: bool
    issues: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_path": self.spec_path,
            "ok": self.ok,
            "skipped": self.skipped,
            "issues": list(self.issues),
        }


def run_lint(spec_path: Path, *, schema_path: Path | None = None) -> LintResult:
    """Lädt eine YAML-Datei und validiert sie gegen das Spec-Schema v0.

    - Wirft `FileNotFoundError`, wenn die Datei fehlt.
    - Wirft `SpecLoaderError` (über `SpecLoader.load`) für nicht-parsbare
      YAML — Adapter-Schicht lässt das nach oben durchschlagen, damit
      MCP `isError: true` mit klarer Diagnose liefern kann.
    - Projekt-Manifeste (kein `kind`-Feld) werden wie in der CLI als
      `skipped=True, ok=True` zurückgegeben.
    """
    if not spec_path.is_file():
        raise FileNotFoundError(f"Spec-Datei nicht gefunden: {spec_path}")

    data = SpecLoader.load(spec_path)
    if not isinstance(data, dict) or "kind" not in data:
        return LintResult(spec_path=str(spec_path), ok=True, skipped=True, issues=[])

    validator = SchemaValidator(schema_path=schema_path)
    issues = [
        {"path": issue.path, "message": issue.message} for issue in validator.iter_issues(data)
    ]
    return LintResult(
        spec_path=str(spec_path),
        ok=not issues,
        skipped=False,
        issues=issues,
    )
