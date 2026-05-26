"""Conformance-Runner (Phase 3 Stage 4 — MVP `static-validate`-Backend).

Pro `(spec, target)`-Paar im Lockfile wird:

1. Die Spec aus dem Registry geladen,
2. Erneut gerendert (`render_for_target`, ReplayCache),
3. Der Output gegen die `generated_files_sha256`-Einträge des Lockfiles
   ge-hashed und drift-detected,
4. Der Validator des jeweiligen Targets erneut explizit aufgerufen
   (`validate_tsx` / `validate_swift` / `validate_ts`), sodass im
   strukturierten Report eindeutig zwischen `render_failed`,
   `hash_drift` und `validator_failed` unterschieden werden kann.

Stage 4 liefert nur den **statischen** Backend (kein externer Build, kein
Visual-Regression). Beides wird in Phase 4 hinter dem
`ConformanceBackend`-Protocol plug-baren Backends nachgereicht (z.B.
`BuildSmokeBackend` mit `npm run build` / `ng build` / `swiftc -parse`).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from speccify_core.codegen import (
    CacheMissError,
    CodegenError,
    LlmClient,
    TargetRender,
    render_for_target,
)
from speccify_core.codegen.angular_llm import validate_ts as _validate_ts
from speccify_core.codegen.react_llm import validate_tsx as _validate_tsx
from speccify_core.codegen.swiftui_llm import validate_swift as _validate_swift
from speccify_core.lockfile import LockEntry, Lockfile
from speccify_core.registry import Registry, RegistryError, Version

__all__ = [
    "ConformanceBackend",
    "ConformanceReport",
    "ConformanceResult",
    "ConformanceStatus",
    "StaticValidateBackend",
    "VALIDATORS",
    "run_conformance",
]


# Status-Codes des Conformance-Runners. Bewusst klein gehalten, damit der
# Report maschinen-lesbar bleibt (CI-Failures pro Status filterbar).
ConformanceStatus = str  # "ok" | "render_failed" | "hash_drift" | "validator_failed" | "no_outputs"


# Validator-Registry pro Target. Neue Targets registrieren sich hier ein.
# `None` heißt "kein Validator verfügbar" (Backend übersprungt den Validator-
# Schritt, behandelt aber Hash-Drift wie gehabt).
class _Validator(Protocol):
    def __call__(self, text: str) -> None: ...  # raises CodegenError on failure


VALIDATORS: dict[str, _Validator] = {
    "react": _validate_tsx,
    "swiftui": _validate_swift,
    "angular": _validate_ts,
}


@dataclass(frozen=True)
class ConformanceResult:
    """Strukturiertes Ergebnis für genau ein `(spec_id, target)`-Paar."""

    spec_id: str
    version: str
    target: str
    status: ConformanceStatus
    messages: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True)
class ConformanceReport:
    """Aggregiertes Ergebnis über alle `(spec, target)`-Paare im Lockfile."""

    results: tuple[ConformanceResult, ...] = ()
    backend: str = "static-validate"

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    def failures(self) -> tuple[ConformanceResult, ...]:
        return tuple(r for r in self.results if not r.ok)

    def by_target(self) -> dict[str, tuple[ConformanceResult, ...]]:
        out: dict[str, list[ConformanceResult]] = {}
        for r in self.results:
            out.setdefault(r.target, []).append(r)
        return {k: tuple(v) for k, v in out.items()}


class ConformanceBackend(Protocol):
    """Backend-Plugin-Slot.

    `static-validate` ist der Phase-3-Default. Phase-4-Backends (Build-Smoke,
    Visual-Regression) implementieren dasselbe Protocol und liefern den
    gleichen `ConformanceReport`-Typ — sodass CLI- und CI-Pfade target-/
    backend-agnostisch bleiben.
    """

    name: str

    def run(
        self,
        *,
        lockfile: Lockfile,
        registry: Registry,
        llm_client: LlmClient,
        targets: tuple[str, ...] | None = None,
    ) -> ConformanceReport: ...


@dataclass
class StaticValidateBackend:
    """Default-Backend in Phase 3: kein externer Build, nur Renderer + Validator + Drift."""

    name: str = field(default="static-validate")

    def run(
        self,
        *,
        lockfile: Lockfile,
        registry: Registry,
        llm_client: LlmClient,
        targets: tuple[str, ...] | None = None,
    ) -> ConformanceReport:
        wanted: set[str] | None = set(targets) if targets else None
        results: list[ConformanceResult] = []
        for entry in lockfile.entries:
            if wanted is not None and entry.target not in wanted:
                continue
            results.append(_run_one(entry, registry=registry, llm_client=llm_client))
        return ConformanceReport(results=tuple(results), backend=self.name)


def _run_one(
    entry: LockEntry,
    *,
    registry: Registry,
    llm_client: LlmClient,
) -> ConformanceResult:
    msgs: list[str] = []

    # 1) Spec laden
    try:
        spec = registry.fetch(entry.id, Version.parse(entry.version))
    except RegistryError as exc:
        return ConformanceResult(
            spec_id=entry.id,
            version=entry.version,
            target=entry.target,
            status="render_failed",
            messages=(f"Spec konnte nicht geladen werden: {exc}",),
        )

    # 2) Re-Render
    try:
        rendered: TargetRender = render_for_target(spec, entry.target, llm_client=llm_client)
    except (CacheMissError, CodegenError, NotImplementedError) as exc:
        return ConformanceResult(
            spec_id=entry.id,
            version=entry.version,
            target=entry.target,
            status="render_failed",
            messages=(f"Re-Render fehlgeschlagen: {exc}",),
        )

    # 3) Hash-Drift gegen Lockfile-Outputs
    expected = {f.path: f.sha256 for f in entry.generated_files_sha256}
    if not expected:
        return ConformanceResult(
            spec_id=entry.id,
            version=entry.version,
            target=entry.target,
            status="no_outputs",
            messages=(
                f"Lockfile-Eintrag {entry.id}@{entry.version} ({entry.target}) hat keine "
                "`generated_files_sha256` (bitte `speccify pull` ausführen).",
            ),
        )

    rendered_paths = set(rendered.files.keys())
    expected_paths = set(expected.keys())
    for path in sorted(rendered_paths - expected_paths):
        msgs.append(f"Output {path} (re-rendered) nicht im Lockfile.")
    for path in sorted(expected_paths - rendered_paths):
        msgs.append(f"Output {path} (Lockfile) nicht erneut gerendert.")
    for path in sorted(rendered_paths & expected_paths):
        digest = f"sha256:{hashlib.sha256(rendered.files[path]).hexdigest()}"
        if digest != expected[path]:
            msgs.append(f"Hash-Drift für {path}: Lockfile={expected[path]}, neu={digest}.")
    if msgs:
        return ConformanceResult(
            spec_id=entry.id,
            version=entry.version,
            target=entry.target,
            status="hash_drift",
            messages=tuple(msgs),
        )

    # 4) Validator explizit (zweite Verteidigungslinie; render_for_target ruft
    # den Validator zwar bereits implizit, aber Conformance soll klar
    # unterscheiden können).
    validator = VALIDATORS.get(entry.target)
    if validator is not None:
        for path in sorted(rendered.files.keys()):
            text = rendered.files[path].decode("utf-8", errors="replace")
            try:
                validator(text)
            except CodegenError as exc:
                return ConformanceResult(
                    spec_id=entry.id,
                    version=entry.version,
                    target=entry.target,
                    status="validator_failed",
                    messages=(f"Validator-Fehler für {path}: {exc}",),
                )

    return ConformanceResult(
        spec_id=entry.id,
        version=entry.version,
        target=entry.target,
        status="ok",
    )


def run_conformance(
    *,
    lockfile: Lockfile,
    registry: Registry,
    llm_client: LlmClient,
    targets: tuple[str, ...] | None = None,
    backend: ConformanceBackend | None = None,
) -> ConformanceReport:
    """Komfort-Wrapper: Default-Backend = `StaticValidateBackend`.

    `targets` filtert das Lockfile auf eine Teilmenge der Targets. `None`
    bedeutet "alle Targets des Lockfiles".
    """
    chosen = backend or StaticValidateBackend()
    return chosen.run(
        lockfile=lockfile,
        registry=registry,
        llm_client=llm_client,
        targets=targets,
    )


# Hilfs-Pfad-Hinweis (für CLI-Output)
def format_report(report: ConformanceReport, *, project_dir: Path | None = None) -> list[str]:
    """Render-Hilfe: erzeugt Zeilen für CLI-Output. Eigenständig testbar."""
    lines: list[str] = []
    for result in report.results:
        prefix = "✓" if result.ok else "✗"
        lines.append(
            f"{prefix} [{result.target}] {result.spec_id}@{result.version} → {result.status}"
        )
        for msg in result.messages:
            lines.append(f"    - {msg}")
    if project_dir is not None and not report.ok:
        lines.append(f"Lockfile: {project_dir}/speccify.lock")
    return lines
