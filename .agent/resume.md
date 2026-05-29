# Resume — Speccify Phase 5b abgeschlossen (alle Stages 0–6 Done)

> Einstiegspunkt für die nächste Session. Letzte Aktualisierung: 2026-05-29 (Phase-5b-Final).

## Status

- **Phase 5b Stage 4 Done** (2026-05-29) — 75-Pfad-Cross-Consistency-Sweep
  in `registry/tests/test_cross_consistency_sweep.py` produktiv:
  `5 Specs × 3 Targets × 5 Pfade (Local/Remote/CLI/MCP/Web)`.
- **Phase 5b Stage 3 Done** (2026-05-29) — Echte Build-Smokes für alle 5
  Referenz-Specs × {Angular, SwiftUI} via `pytest.mark.parametrize`.
  Synthetische Mini-Snippets in `core/tests/test_conformance_build_smoke.py`
  ersetzt; `_render_spec`/`_lock_entry_for` als target-agnostische Helfer.
- **Phase 5b Stage 2 Done** (2026-05-29 durch User) — Replay-Cache-Fixtures
  für `5 Specs × {angular, swiftui}` committed (12 neue JSONs unter
  `tests/fixtures/llm-cache/`).
- **Phase 5b Stage 1 Done** (2026-05-27) — `scripts/record_llm_cache.py` ist
  target-aware.
- **Phase 5b Stages 5+6 Done** (2026-05-29) — Stage 5: CI-Review ergab
  keinen YAML-Change (Sweep läuft automatisch im bestehenden
  `registry-backend`-Job); README + `docs/conformance.md` aktualisiert.
  Stage 6: Plan archiviert nach
  `.agent/plans/archive/phase-5b-conformance-sweep.md`.
- **Kein aktiver Plan** in `.agent/plans/` (außer Master-Plan).
  **Tag-Vorschlag an User: `v0.9.0-phase-5b`** (selbst nicht gesetzt, vgl. `rules.md`).
- **Phase 5a** abgeschlossen, Tag `v0.8.0-phase-5a` **gesetzt** (Commit 7845844).
- **Phase 4** abgeschlossen; Tag-Vorschlag `v0.7.0-phase-4` (offen).
- **Phase 3** abgeschlossen; Tag-Vorschlag `v0.6.0-phase-3` (offen).
- **Phase 2** abgeschlossen; Tag-Vorschlag `v0.5.0-phase-2` (offen).

## Verifikation Phase 5b Stage 4

- **Root-Pytest (Default, `-m "not conformance"`)**: **332 passed**, 12
  deselected (unverändert — neue Tests sind im Registry-Paket).
- **Registry-Pytest**: **134 passed** in ~5 s (+15 ggü. Stage 3: 119 → 134).
- **Sweep-Subset isoliert**: 15 Sweep-Parametrisierungen passed in 2.77 s.
- **Root-Pytest (`-m conformance`)**: 11 passed (unverändert ggü. Stage 3).
- `ruff check` → All checks passed. `ruff format --check` → 145 files already formatted.

## Verifikation Phase 5a (final)

- **Root-Pytest (Default, `-m "not conformance"`)**: **325 passed** (+13 ggü. Phase 4 = 312); 3 deselected.
- **Root-Pytest (`-m conformance`)**: **3 passed** in 6.17 s lokal (React/Angular/SwiftUI Build-Smoke).
- **Registry-Pytest**: **119 passed** (unverändert).
- **Gesamt regulär: 444 Tests grün.**
- `ruff check` → All checks passed.
- `ruff format --check` → 143 files already formatted.

## Was Phase 5a geliefert hat

- **Stage 0**: 10 Open Questions vom User mit „folge deinen Empfehlungen" beantwortet (Toolchain-Pinning lokal, Conformance-Marker mit Default-Exclude, Speicherort in `core/`, `toolchain_missing` ≠ Failure).
- **Stage 1**: `BuildSmokeBackend` + `ToolchainDriver`-Protocol in `core/src/speccify_core/conformance_build_smoke.py`; `ReactToolchainDriver` via `npm install` + lokales `tsc --noEmit` (`typescript@5.4.5` + `@types/react@18.2.79`).
- **Stage 2** (Follow-up): `AngularToolchainDriver` analog — `@angular/core@17.3.0` + `@angular/common@17.3.0` + `rxjs@7.8.1` + `zone.js@0.14.4`; `tsc --noEmit` mit `experimentalDecorators=true`/`emitDecoratorMetadata=true`. E2E-Test mit synthetischem `@Component`-Snippet (Replay-Cache-Blocker umgangen — Phase-5a-Scope ist der Driver-Pfad, Cross-Spec-Coverage bleibt Phase 5b).
- **Stage 3** (Follow-up): `SwiftUIToolchainDriver` via `xcrun --sdk macosx swiftc -typecheck`. macOS-only; Linux-CI skippt sauber via `toolchain_missing`. E2E-Test mit synthetischem `View`-Snippet.
- **Stage 4** (Follow-up): Separater Workflow `.github/workflows/conformance.yml` mit 3 Jobs (`conformance-react`/`-angular` auf Ubuntu+Node 20, `conformance-swiftui` auf macOS-latest). Trigger: Path-Filter auf `conformance_build_smoke.py`/`codegen/**`/Test-Datei + `schedule: 17 3 * * *` nightly + `workflow_dispatch`. Default-CI (`ci.yml`) unverändert.
- **Stage 5**: `docs/conformance.md` (122 LOC) — Konzept, Targets-Tabelle, Lokal-Walkthrough, CI-Verhalten, Backend-API, Scope-Tabelle 5a vs. 5b; README-Link aktualisiert; Plan-Status-Block aktualisiert; AGENTS.md + resume.md aktualisiert.

## Nächster Schritt — Phase-5c-Plan-Entwurf nach User-Tag

Phase 5b ist komplett durch. Nach dem User-Tag `v0.9.0-phase-5b` ist der
nächste Schritt ein Phase-5c-Plan-Entwurf. Kandidaten (aus dem alten
Phase-5b-Backlog, in Phase 5b bewusst out-of-scope gelassen):

1. **Visual-Regression-Skeleton** — Screenshot-Vergleich gegen Spec-`screenshots[]` (Tooling-OQ: pixelmatch+Playwright vs. PIL.ImageChops).
2. **Echtes `ng build`** statt nur `tsc --noEmit` für Angular (volle AOT-Pipeline).
3. **Web-Backend Workspace-aware** — bisher explizit out-of-scope in Phase 4.
4. **Spec-Schema-Bump** für Visual-Regression-Felder (falls (1) gewählt wird).

Vor Implementierung: Stage 0 = Open Questions an User (analog Phase 3/4/5a/5b-Disziplin).

## Phase-5a-Recap (Plan-Entwurf nach User-Tag)

Kandidaten (aus Phase-5a-Stage-0-Decisions + Plan-OQ5):

1. **Replay-Cache-Recording**: User triggert `BEDROCK_RECORD=1`, Cache für `5 Specs × {angular, swiftui}` wird unter `tests/fixtures/llm-cache/` committed.
2. **75-Pfad-Cross-Consistency-Sweep**: `5 Specs × 3 Targets × 5 Pfade (Local/Remote/CLI/MCP/Web)` parametrisiert.
3. **Echte Spec×Target-Build-Smoke-Erweiterung**: Angular/SwiftUI nicht mehr nur synthetisch, sondern alle 5 Referenz-Specs durch den Driver.
4. **Visual-Regression-Skeleton** (Stretch): Screenshot-Vergleich gegen Spec-`screenshots[]`.
5. **Echtes `ng build`** (Stretch über `tsc --noEmit` hinaus).
6. **Web-Backend Workspace-aware** (Phase 5c, separat).

Vor Implementierung: Stage 0 = Open Questions an User (analog Phase 3/4/5a-Disziplin).

## Befehle (Spickzettel)

```bash
# Hidden-Flag entfernen (jedes Mal nach uv sync nötig) — läuft auch automatisch via conftest.py
chflags nohidden .venv/lib/python3.12/site-packages/*.pth

# Default-Tests (ohne Conformance)
.venv/bin/python -m pytest -q

# Conformance-Tests (Opt-in, lokal mit npm + xcrun verifiziert)
.venv/bin/python -m pytest -m conformance core/tests/test_conformance_build_smoke.py -v

# Registry-Tests
cd registry && ../.venv/bin/python -m pytest -q

# Lint + Format
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

## Pflichtlektüre vor Code

1. `AGENTS.md` (Aktuelle Phase + Konventionen).
2. `.agent/agent.md` + `.agent/rules.md` (Sprache: Deutsch, Du; FP-Stil; Tests pflicht; Tags nur User).
3. `docs/conformance.md` (Phase-5a-Doku, Decisions + CLI-Walkthrough).
4. `docs/workspaces.md` (Phase-4-Doku).
5. `.agent/plans/archive/phase-5a-conformance-backends.md` (Phase-5a-Plan mit finalem Status-Block oben).
