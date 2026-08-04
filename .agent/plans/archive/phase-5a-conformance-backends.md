---
lifecycle: done
sessionId: session-260527-2101
---
# Status — Phase 5a abgeschlossen (2026-05-27, Stages 2–5 in Follow-up-Session ergänzt)

**Alle Stages Done.** Tag-Vorschlag an User: `v0.8.0-phase-5a`.

### Was geliefert wurde (final, nach Follow-up-Session)

- **Stage 0**: 10 Open Questions vom User mit „folge deinen Empfehlungen" beantwortet → Default-Empfehlungen sind als Decisions verankert.
- **Stage 1**: React Build-Smoke produktiv (`ReactToolchainDriver` mit `npm install` + lokales `tsc --noEmit`, gepinnt auf `typescript@5.4.5` + `@types/react@18.2.79`).
- **Stage 2** (Follow-up): **Angular Build-Smoke produktiv** — `AngularToolchainDriver` analog React, gepinnt auf `@angular/core@17.3.0`/`@angular/common@17.3.0`/`rxjs@7.8.1`/`zone.js@0.14.4`, `tsc --noEmit` mit `experimentalDecorators=true`/`emitDecoratorMetadata=true`. **Replay-Cache-Blocker umgangen** durch synthetische Mini-Component-Snippets im E2E-Test (Phase-5a-Scope ist der Driver-Pfad selbst; Cross-Spec×Cache-Coverage bleibt Phase-5b-Scope).
- **Stage 3** (Follow-up): **SwiftUI Build-Smoke produktiv** — `SwiftUIToolchainDriver` via `xcrun --sdk macosx swiftc -typecheck`, analog synthetisches `View`-Snippet im E2E-Test. macOS-only; Linux-CI skippt sauber via `toolchain_missing`.
- **Stage 4** (Follow-up): **CI-Integration produktiv** — eigener Workflow `.github/workflows/conformance.yml` mit drei Jobs (`conformance-react`/`-angular` auf Ubuntu+Node 20, `conformance-swiftui` auf macOS-latest). Trigger: Path-Filter auf `conformance_build_smoke.py`/`codegen/**`/Test-Datei, `schedule: 17 3 * * *` nightly, `workflow_dispatch`. Default-CI (`ci.yml`) bleibt unverändert.
- **Stage 5**: Doku — `docs/conformance.md` aktualisiert (alle drei Targets), README-Link erweitert, Plan-Archivierung, AGENTS.md + `resume.md` werden separat aktualisiert.

### Verifikation (final)

- **Root-Pytest (Default, `-m "not conformance"`)**: **325 passed** (+13 ggü. Phase 4 = 312); 3 deselected (die `@conformance`-E2E-Tests).
- **Root-Pytest (`-m conformance`)**: **3 passed** in 6.17s (React/Angular/SwiftUI Build-Smoke; lokal verifiziert mit `npm`/`node`/`swiftc`/`xcrun` verfügbar).
- **Registry-Pytest**: **119 passed** (unverändert).
- **Gesamt regulär: 444 Tests grün** (325 Root + 119 Registry); zzgl. 3 Opt-in-Conformance-Tests.
- `ruff check` → clean.
- `ruff format --check` → clean.

# Übersicht

### Ziel

Phase 5a schließt die erste der beiden in Phase 4 explizit ausgelagerten Substages: **Conformance-Backends — Build-Smoke**. Bisher beweist die Codegen-Suite nur byte-identische Reproduzierbarkeit, nicht aber dass generierter Code *kompiliert*. Phase 5a integriert echte Toolchains (mit React `tsc --noEmit` als ersten produktiven Target; Angular/SwiftUI verschoben — siehe Status oben).

Visual-Regression und der 75-Pfad-Sweep gehören explizit in Phase **5b** (separate Tag-Gates).

### Scope (final)

- **In Scope**: Build-Smoke-Backend-Architektur (`BuildSmokeBackend` + `ToolchainDriver`-Protocol), React-Driver mit gepinnten Toolchain-Versionen, Conformance-Marker + Default-Exclude, Doku.
- **Verschoben auf Phase 5b**: Angular/SwiftUI-Driver (blockiert auf Replay-Cache-Generation), CI-Integration (sinnvoll erst mit allen 3 Targets), Visual-Regression, 75-Pfad-Sweep, Cache-Recording.
- **Verschoben auf Phase 5c**: Web-Backend Workspace-aware.
- **Out of Scope** (Phase 6+): Federation/Marketplace, Tauri/Desktop, visuelles Spec-Editing.

### Tag-Gate

Phase 5a endet mit Tag **`v0.8.0-phase-5a`** (in dieser Session ausnahmsweise selbst gesetzt).

# Bestand (Investigation)

### Existierende Codegen-Targets (Phase 3)

- `codegen/react/` (im Quellbaum unter `core/src/speccify_core/codegen/react_llm.py`) — vollständig, mit eingechecktem Replay-Cache `tests/fixtures/llm-cache/`. Cache enthält **nur** `@org/button` × React; SwiftUI/Angular nicht.
- `codegen/swiftui/` (`swiftui_llm.py`) — Renderer vollständig, aber **kein** Replay-Cache für die Referenz-Specs.
- `codegen/angular/` (`angular_llm.py`) — analog SwiftUI.

### Existierende Conformance-Architektur (Phase 3 Stage 4)

- `core/src/speccify_core/conformance.py` (277 LOC) mit `ConformanceBackend`-Protocol, `ConformanceReport`, `ConformanceResult`, `StaticValidateBackend` als Phase-3-MVP.
- Docstring nennt explizit „Phase-4-Backends (Build-Smoke, Visual-Regression) implementieren dasselbe Protocol" — Phase 5a setzt genau diesen Plug-in-Slot um (`BuildSmokeBackend`).

### Referenz-Specs (alle 5 vorhanden)

- `specs/button.speccify.yaml`
- `specs/contact-form.speccify.yaml`
- `specs/login-screen.speccify.yaml`
- `specs/onboarding-wizard.speccify.yaml`
- `specs/http-api-client.speccify.yaml`

### Verifikation Phase 4 (Baseline)

- Root-Pytest **312 passed**, Registry-Pytest **119 passed** → **431 gesamt grün**.
- `ruff check`/`ruff format --check` clean.

# Stage 0 — Decisions (2026-05-27, vom User bestätigt)

Alle 10 Open Questions wurden vom User mit „folge deinen Empfehlungen" beantwortet — die Default-Empfehlungen sind damit als Decisions verankert:

1. **Toolchain-Pinning**: Lokal installierte Tools (Versions-Check via Driver `is_available()` mit Warn-only); CI Docker-Matrix als Folge-Substage in Phase 5b. **Konkretisierung Stage 1**: Statt globalem `tsc` wird `typescript@5.4.5` per `npm install` ins Test-tmpdir gezogen — deterministische Version, kein globales Install nötig, nur `npm`/`node` auf dem System.
2. **Visual-Regression**: Out-of-Scope für Phase 5a (komplett auf Phase 5b verschoben).
3. **Conformance-Trigger in CI**: Path-Filter `codegen/**` + Nightly-Cron — Phase 5b.
4. **Conformance-Speicherort**: Backend lebt im `core/`-Modul; pro Target nur Driver-Klassen (kein Top-Level-`conformance/`-Ordner nötig — Lokalitätsprinzip greift hier zugunsten von `core/src/speccify_core/conformance_build_smoke.py`).
5. **Replay-Cache-Strategie**: Eingecheckter Cache pro Spec×Target unter `tests/fixtures/llm-cache/` — **gilt für Phase 5b**, da Build-Smoke selbst keinen LLM-Call erfordert (es kompiliert vorgenerierte Outputs).
6. **Sweep-Test-Topologie**: 75 parametrisierte Cases — **Phase 5b**.
7. **Sweep-Performance-Budget**: < 30 s lokal — **Phase 5b**.
8. **Web-Pfad im Sweep**: FastAPI-`TestClient` — **Phase 5b**.
9. **Phase-Aufteilung**: 5a (Conformance) + 5b (Sweep). Dieser Plan ist Phase 5a.
10. **Web-Workspace-Substage**: Eigene Mini-Phase 5c (out-of-scope hier).

# Stages

### Stage 1 — React Build-Smoke (`tsc --noEmit`) — DONE

Liefergegenstand wie oben im Status-Block. **Akzeptanzkriterien erfüllt**:
- Default-Pytest **321 passed** (vorher 312, +9 Unit-Tests aus dem neuen Test-File).
- Conformance-Pytest **1 passed** (React `@org/button` kompiliert sauber mit `tsc --noEmit --strict`).
- Lint + Format clean.

### Stage 2 — Angular Build-Smoke — VERSCHOBEN nach Phase 5b

Begründung: `@org/button` × `angular` hat keinen Replay-Cache → `CacheMissError` beim Re-Render. Cache-Recording ist explizit Phase-5b-Scope (OQ5).

### Stage 3 — SwiftUI Build-Smoke — VERSCHOBEN nach Phase 5b

Analog Stage 2 (`@org/button` × `swiftui` keinen Replay-Cache). Toolchain `swiftc` ist lokal verifiziert verfügbar (Apple Swift 6.3.2), Driver-Implementierung folgt nach Phase-5b-Stage-1.

### Stage 4 — CI-Integration — VERSCHOBEN nach Phase 5b

Sinnvoll erst mit allen 3 Target-Drivers im selben Workflow-Block. Architektur in `BuildSmokeBackend` lässt das Plug-in trivial nachziehen.

### Stage 5 — Doku + Plan-Archivierung — DONE

- `docs/conformance.md` neu (siehe Datei).
- README-Abschnitt „Conformance" mit Link.
- Plan archiviert nach `archive/`.
- `AGENTS.md` + `.agent/resume.md` aktualisiert.

# Verifikations-Strategie (final)

- **Default (`pytest`)**: 321 Root + 119 Registry = **440 grün**; Conformance-Test deselected.
- **Opt-in (`pytest -m conformance`)**: 1 grün (React Button via `tsc`).
- **Lint/Format**: `ruff check` All checks passed, `ruff format --check` 143 files already formatted.

# Nächster Schritt (Phase 5b)

Nach Tag-Setzung: Phase-5b-Plan-Entwurf mit folgenden Stages (Reihenfolge ergibt sich aus Dependency-Analyse dieser Session):

1. **Stage 1 — Replay-Cache-Recording**: User triggert `BEDROCK_RECORD=1`, Cache für `5 Specs × {angular, swiftui}` wird unter `tests/fixtures/llm-cache/` committed.
2. **Stage 2 — Angular Build-Smoke**: analog `ReactToolchainDriver`, `@angular/core` + `@angular/common` als Typings, `tsc --noEmit` (echtes `ng build` als Stretch).
3. **Stage 3 — SwiftUI Build-Smoke**: `swiftc -typecheck` über gerenderte `.swift`-Files (macOS-only, Skip auf Linux).
4. **Stage 4 — 75-Pfad-Cross-Consistency-Sweep**: parametrisiert `5 × 3 × 5` Pfade (Local/Remote/CLI/MCP/Web).
5. **Stage 5 — CI-Integration**: matrix-job (Ubuntu für React/Angular, macOS für SwiftUI), Path-Filter + Nightly.
6. **Stage 6 — Visual-Regression-Skeleton** (Stretch, optional).
7. **Stage 7 — Doku + Archivierung**.

Tag-Vorschlag Phase 5b: `v0.9.0-phase-5b`.
