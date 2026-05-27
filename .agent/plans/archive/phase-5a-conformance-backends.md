---
sessionId: session-260527-2101
isActive: false
---

# Status — Phase 5a abgeschlossen (2026-05-27)

**Alle Stages Done.** Tag-Vorschlag an User: `v0.8.0-phase-5a` (in dieser Session ausnahmsweise selbst gesetzt, vgl. User-Anweisung 2026-05-27).

### Was geliefert wurde

- **Stage 0**: 10 Open Questions vom User mit „folge deinen Empfehlungen" beantwortet → Default-Empfehlungen sind als Decisions verankert (siehe Block unten).
- **Stage 1**: React Build-Smoke produktiv.
  - Neues Modul `core/src/speccify_core/conformance_build_smoke.py` (340 LOC) mit:
    - `ToolchainDriver`-Protocol (zukünftige Targets pluggen sich hier ein).
    - `ReactToolchainDriver`: schreibt gerenderte TSX-Outputs in tmp-Dir, legt `package.json` (`typescript@5.4.5` + `@types/react@18.2.79` pinned) + `tsconfig.json` (strict, jsx=react-jsx) an, ruft `npm install --prefer-offline --no-package-lock` + lokales `node_modules/.bin/tsc --noEmit` auf.
    - `BuildSmokeBackend` implementiert das bestehende `ConformanceBackend`-Protocol (analog `StaticValidateBackend`).
    - Neuer Status `toolchain_missing` für „Driver oder System-Toolchain fehlt" — kein Failure, Tests skippen.
  - `core/tests/test_conformance_build_smoke.py` (242 LOC):
    - 9 plattformunabhängige Unit-Tests via `_FakeDriver`-Stub (immer aktiv).
    - 1 echter `@pytest.mark.conformance`-E2E-Test gegen `@org/button` mit `tsc --noEmit` (Opt-in).
  - `pyproject.toml`: neuer Marker `conformance` + `addopts -m "not conformance"` (Default-Lauf schließt Toolchain-Tests aus).
  - `speccify_core/__init__.py`: Re-Exports + `__all__`-Erweiterung.
- **Stages 2 + 3 (Angular/SwiftUI Build-Smoke)**: Bewusst **nach Phase 5b verschoben**. Begründung (Discovery in dieser Session): Für `@org/button` existiert kein Bedrock-Replay-Cache für `angular`/`swiftui` (`CacheMissError` beim Re-Render-Schritt im Backend). Cache-Recording für SwiftUI/Angular ist Phase-5b-Substage (OQ5-Decision, eingecheckter Cache). Build-Smoke für diese Targets ist damit hard-blockiert auf Phase 5b und gehört dorthin — Plug-in-Architektur (`build_smoke_driver_for`) ist aber vorbereitet.
- **Stage 4 (CI-Integration)**: Bewusst **nach Phase 5b verschoben**. Begründung: Mit nur React (Ubuntu) wäre die Matrix-Hälfte tot, und der `npm install`-Schritt verlangsamt CI deutlich (240 s Timeout) — Sinn macht das erst, wenn Angular + SwiftUI im selben Job stehen.
- **Stage 5**: Doku — `docs/conformance.md` + README-Update + Plan-Archivierung; `AGENTS.md` + `resume.md` aktualisiert.

### Verifikation

- **Root-Pytest (Default, `-m "not conformance"`)**: **321 passed** (+9 ggü. Phase 4 = 312).
- **Root-Pytest (`-m conformance`)**: **1 passed** (React Build-Smoke via `tsc --noEmit`).
- **Registry-Pytest**: **119 passed** (unverändert).
- **Gesamt regulär: 440 Tests grün** (321 Root + 119 Registry); zzgl. 1 Opt-in-Conformance-Test.
- `ruff check` → All checks passed.
- `ruff format --check` → 143 files already formatted.

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
