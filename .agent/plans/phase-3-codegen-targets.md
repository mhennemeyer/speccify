---
sessionId: session-260524-171600-3a
isActive: true
---

# Requirements

## Phase-3-Ziel: Zweites + drittes Codegen-Target + Conformance-Runner + Workspaces

Phase 1b hat **React** als erstes echtes Codegen-Target geliefert. Phase 2 hat den **Registry-MVP** gebaut (Publish/Fetch/Yank/Search/Web-UI/Resolver-Remote). In Phase 3 wird das Codegen-Ökosystem **multi-target**: aus einer `speccify.yaml`-Spec entstehen deterministisch Komponenten für **mindestens zwei weitere Targets** plus ein **Conformance-Runner**, der pro Target prüft, dass das generierte Artefakt die Akzeptanzkriterien der Spec tatsächlich erfüllt. Ergänzend zieht **Workspaces** aus Phase 2 nach: ein `workspaces: [...]`-Feld im Manifest erlaubt Mono-Repos mit mehreren Manifesten (Cargo-/pnpm-Parität).

Aus dem Master-Plan: „SwiftUI und Angular als Targets (oder Jetpack Compose, je nach Pilot-Use-Case). React ist bereits in Phase 1b geliefert. Conformance-Runner pro Target: Docker + Playwright + Snapshot-Tests."

## In Scope

- **Zweites Codegen-Target** (Pilot, Stack-Auswahl in Stage 0): voller Codegen-Pfad analog zu React — Renderer in `codegen/`, Template-/Prompt-Replay-Cache, Golden Renders pro Referenz-Spec, byte-identische Determinismus-Tests.
- **Drittes Codegen-Target**: zweiter Renderer im selben Pattern, um zu beweisen, dass die Codegen-Abstraktion „target-agnostisch" trägt (keine target-spezifische Sonderlogik in `speccify_core`).
- **Conformance-Runner pro Target**: dockerisierter Test-Harness, der pro Target das generierte Artefakt baut und gegen die `acceptance_criteria` der Spec prüft (Snapshot- und/oder interaktive Tests, je nach Target).
- **Workspaces**: `workspaces: [path/glob]` im Manifest; CLI-Commands (`lock`/`pull`/`verify`) iterieren über alle Member-Manifeste; Lockfile-Layout entscheidet Stage 0 (ein zentrales Root-Lockfile vs. ein Lockfile pro Member, analog Cargo/pnpm).
- **Multi-Target im Manifest**: heute `target: react`; künftig `targets: [react, swiftui]` oder Manifest-pro-Target — Stage 0 entscheidet.
- **CI**: Conformance-Runner-Jobs pro Target (Docker-basiert; Caching via GitHub Actions Cache).
- **Master-Plan-/AGENTS-Sync** + Phase-3-Archiv + Tag-Vorschlag `v0.6.0-phase-3` am Ende.

## Out of Scope (bewusst vertagt)

- **Federation / Marketplace** (`speccify.io`-Index, registry-gebundene Föderation) — Phase 4+.
- **Volle sigstore-Verifikation + Transparency-Log** (Phase 2 hat den Slot, die Signatur-Pipeline kommt später).
- **WebAuthn / Hardware-Keys** (Phase 2 = TOTP-only).
- **OAuth-Login** (Phase 2 = Device-Code, Phase 6 nach Master-Plan).
- **Desktop/Tauri-Tooling** (Phase 4 weiterhin on-hold).
- **Visuelles Authoring** (Phase 5+).
- **Echte Live-Domain / Hosted-Registry** (bleibt Phase 4 + Infra-Entscheidung).

## Erfolgskriterien

1. **Mindestens zwei neue Targets** liefern für die fünf Phase-0-Referenz-Specs ein deterministisches Artefakt (zwei `pull`-Aufrufe → byte-identisch).
2. **Conformance-Runner** läuft pro Target lokal (`uv run` / Docker) und in CI; Pflicht-Akzeptanzen aus der Spec werden geprüft.
3. **Workspaces**: ein Workspace mit ≥ 2 Member-Manifesten lässt sich locken, pullen und verifyen; `verify` schlägt zuverlässig bei Drift in **einem** Member fehl.
4. **Cross-Consistency** für jedes neue Target: CLI ↔ MCP ↔ Web (Render-Endpoint) liefern byte-identische Artefakte (analog Phase-1d-Vertrag).
5. **CI grün** auf allen neuen Jobs; bestehende Jobs unverändert.


# Architecture & Decisions

## Open Questions Round 1 (Stage 0 vor Code-Stages)

Bevor wir Delivery-Stages konkretisieren, müssen folgende Punkte mit dem User geklärt werden. Reihenfolge entspricht der Klärungspriorität: 1–4 sind blocker für jeglichen Code; 5–10 lassen sich später ohne Re-Work nachholen.

1. **Zweites Target (Pilot)** — SwiftUI, Angular oder Jetpack Compose? Auswahlkriterien: (a) Pilot-Use-Case, (b) Reichweite der Spec-Sprache (Inputs/Outputs/Events), (c) Test-Harness-Aufwand. Master-Plan-Tendenz: „SwiftUI **oder** Angular **oder** Jetpack Compose, je nach Pilot-Use-Case".
2. **Drittes Target** — die beiden anderen aus 1, oder zuerst nur **eines** voll fertig + Conformance-Runner und das dritte als Folge-Phase? Risiko-Tradeoff: Tiefe vs. Breite.
3. **Conformance-Runner-Stack** — Docker + Playwright (Web-Targets), Docker + Xcode-Simulator (SwiftUI), Docker + Espresso/Robolectric (Compose). Ein gemeinsames Harness-Konzept oder pro Target eigene Toolchain?
4. **Workspaces-Layout** — ein zentrales `speccify.lock` im Workspace-Root (Cargo-Stil) oder ein Lockfile pro Member (pnpm-Stil)? Auswirkungen auf Determinismus, Drift-Erkennung, `add`/`remove`-Semantik.
5. **Multi-Target im Manifest** — `targets: [react, swiftui]` (Liste, Cross-Product im Lockfile) **oder** ein Manifest pro Target (`speccify.yaml` + `speccify.swiftui.yaml`) **oder** Target erst zur `pull`-Zeit via Flag? Konsequenz für Lockfile-Schema (Phase-2-`schema_version: 2` → ggf. v3).
6. **Codegen-Modus pro Target** — `kind: template` (Jinja-Templates) wie React in Phase 1b, oder `kind: llm` mit Replay-Cache (analog Phase 1d Playground-Backend)? Pro Target getrennt entscheidbar.
7. **Golden-Renders pro Target** — `tests/fixtures/golden/<target>/<scope>/<name>.<ext>` als Snapshot-Quelle (Phase-1b-Pattern fortführen) oder Conformance-Runner-Output als Single-Source-of-Truth?
8. **Visuelles Referenz-Material in Specs** — Phase-0-Schema erlaubt `screenshots[]`. Sollen Conformance-Runner diese als Pflicht-Eingabe behandeln (z. B. Visual-Regression) oder bleibt das informativ? Master-Plan-Tendenz: Conformance-Runner = funktional, Visual-Regression später.
9. **Workspaces-Resolver-Semantik** — bei zwei Membern, die dieselbe Spec mit unterschiedlichen Versionen ziehen: globale MVS-Auflösung (eine Version für alle Member, Cargo-Stil) oder pro Member separat (pnpm-Stil mit potenziell mehreren Versionen koexistierend)?
10. **MCP-Tools für neue Targets** — bestehende Tools (`render`, `pull`, `verify`) target-agnostisch erweitern, **oder** pro neuem Target ein zusätzliches Convenience-Tool (`render_swiftui` etc.)? Master-Plan-Tendenz: bestehende Tools target-agnostisch belassen, Target via Argument.

## Decisions (Stage 0, 2026-05-24)

User-Antworten auf die 10 Open Questions Round 1:

1. **Zweites + drittes Target**: **SwiftUI + Angular** — Mobile/Native + Enterprise-Web, größte Reichweite der Spec-Sprache. Beide in Phase 3 (siehe 10).
2. **Drittes Target Timing**: beide neuen Targets vollständig in Phase 3 (Master-Plan-Ziel voll erfüllt; größerer Scope wird über Stage-Granularität gesteuert).
3. **Conformance-Runner-Stack**: **MVP = Build-Smoke + Snapshot-Diff** pro Target. Voll-interaktive Tests (Playwright/Simulator-Klicks) bleiben Phase 4. Plus Visual-Regression gegen Spec-`screenshots[]` (siehe 7).
4. **Workspaces-Lockfile-Layout**: **Cargo-Stil — ein zentrales `speccify.lock` im Workspace-Root**; globale MVS über alle Member (siehe 8).
5. **Multi-Target-Manifest**: **`targets: [react, swiftui, angular]` Liste** im Manifest; Lockfile bekommt Cross-Product. **Lockfile-Schema-Bump v2 → v3** nötig (Backward-Compat-Migration analog v1→v2 aus Phase 2).
6. **Codegen-Modus**: **`kind: llm` mit Replay-Cache für alle neuen Targets** — konsistent mit dem real ausgelieferten React-Renderer aus Phase 1b (`react_llm.py` + `ReplayCacheClient`). Determinismus über Replay-Fixtures (sha256-gehasht via `CacheKey`), nicht über Jinja-Templates. Korrigiert die ursprüngliche Stage-0-Notiz, die fälschlich `kind: template` als Phase-1b-Status angenommen hatte.
7. **Golden Renders**: **`tests/fixtures/golden/<target>/<scope>/<name>.<ext>`** — Phase-1b-Pattern fortführen; Snapshot-Quelle separat vom Conformance-Runner.
8. **Screenshots in Specs**: **Pflicht-Eingabe — Visual-Regression** im Conformance-Runner. Spec-`screenshots[]` werden gegen Render-Output verglichen (z. B. Playwright visual snapshot, SwiftUI snapshot-Test).
9. **Workspaces-Resolver-Semantik**: **Globale MVS (Cargo-Stil)** — eine Version pro Spec für den gesamten Workspace; ConflictError bei unvereinbaren Ranges (Quell-Trace pro Member).
10. **MCP-Tools**: **target-agnostisch via Argument** — `render`/`pull`/`verify` erhalten `target`-Parameter; Tool-Anzahl bleibt 8 (kein `render_swiftui` etc.).

Konsequenzen für die Delivery-Stages:
- Lockfile-Schema-Bump (v3) und Codegen-Abstraktion (Target-Registry) müssen **vor** den Target-Renderern stehen.
- Conformance-Runner = Snapshot + Visual-Regression (kein Docker-Playwright-Interaktions-Setup in Phase 3 — Phase 4).
- Workspaces sind eigene Stage (Cargo-Stil + globale MVS), nicht in jede Target-Stage verteilt.
- SwiftUI-Renderer + Snapshot-Tests laufen in CI **ohne** Xcode-Simulator (reiner Source-Codegen + textuelle Snapshot-Diffs; macOS-Runner für Build-Smoke optional, dann nur job-level skip-on-non-macOS).


# Delivery Stages

## Stage 0: Open Questions klären + Decisions festschreiben — **Done (2026-05-24)**

- 10 Open Questions strukturiert mit User durchgegangen.
- Decisions dokumentiert (oben).
- Round-2-Delivery-Steps (Stages 1–8) konkretisiert.

## Stage 1: Codegen-Abstraktion härten + Lockfile-Schema-Bump v3

Outcome: `speccify_core` hat ein generisches `Renderer`-Interface + `Target`-Registry; Lockfile v3 unterstützt `targets: [...]`-Cross-Product mit v2→v3-Migration; React-Codegen aus Phase 1b auf das neue Interface portiert; alle bestehenden Tests grün.

- `core/src/speccify_core/codegen/__init__.py`: `Renderer`-Protocol (`render(spec, target) -> dict[str, bytes]`, `generator_pin() -> GeneratorPin`); `TARGETS: dict[str, Renderer]` Registry; React-Renderer aus Phase 1b registriert.
- `schema/lockfile.v2.schema.json` als Snapshot (analog v1-Archivierung).
- `schema/lockfile.schema.json` auf v3: `LockEntry` bekommt `target`-Feld + `generated_files_sha256` pro Target; `Lockfile.targets: list[str]` top-level; In-Memory v2→v3-Migration im Loader.
- `core/src/speccify_core/manifest.py`: `target: str` → `targets: list[str]` (mit v0-Manifest-Compat: single `target` wird zu `[target]`).
- Tests: `core/tests/test_lockfile_v3.py` (Migration, Round-Trip, Multi-Target-Entries), `core/tests/test_renderer_protocol.py` (TARGETS-Registry, React-Renderer via Protocol).
- CLI/MCP-Adapter (`pull`, `verify`) lesen `targets`-Liste, iterieren — kein Verhaltenschange bei Single-Target.

## Stage 2: SwiftUI-Renderer (`kind: llm` + Replay-Cache) + Golden Renders

Outcome: `speccify pull --target swiftui` erzeugt deterministisch SwiftUI-`.swift`-Dateien für die 5 Phase-0-Specs; Golden Renders unter `tests/fixtures/golden/swiftui/...`; Replay-Cache-Fixtures unter dem etablierten Phase-1b-Pfad.

- `core/src/speccify_core/codegen/swiftui_llm.py` analog zu `react_llm.py`: Prompt-Builder (Inputs/Outputs/Events/Acceptance → SwiftUI-Bindings), `render_to_files(spec, llm_client) -> (files, cache_key)`; Output-Pfad `<scope>/<name>.swift`.
- Generator-Pin: `kind: llm`, `provider/model/prompt_version=0.1.0`, deterministischer `cache_key` aus Spec-Bytes + Prompt-Version.
- `render_for_target` Dispatcher um `target == "swiftui"` erweitern; `SUPPORTED_TARGETS` ergänzen.
- Replay-Fixtures unter `tests/fixtures/replay/swiftui/<cache_key>.json` (einmalig erzeugt, dann CI-Offline-Mode).
- Golden Renders für alle 5 Referenz-Specs (`button`, `text-field`, `card`, `login-screen`, `onboarding-wizard`) in `tests/fixtures/golden/swiftui/org/<name>.swift`.
- Tests: `core/tests/test_codegen_swiftui.py` (Determinismus via Replay, Golden-Match, Inputs/Events korrekt gebunden, Pflicht-Akzeptanzen im Output als Kommentar-Hinweis), `CacheMissError` ohne Fixture.
- CLI: `speccify pull --target swiftui --out ./out` (kein neues Command, nur Dispatcher-Erweiterung).

## Stage 3: Angular-Renderer (`kind: llm` + Replay-Cache) + Golden Renders

Outcome: `speccify pull --target angular` erzeugt deterministisch Angular-Komponenten (`.component.ts` + `.component.html` + `.component.css`) für die 5 Phase-0-Specs; Replay-Cache-Fixtures analog SwiftUI.

- `core/src/speccify_core/codegen/angular_llm.py` analog zu `react_llm.py`/`swiftui_llm.py`: Prompt-Builder, `render_to_files(spec, llm_client) -> (files, cache_key)`; Output-Pfad `<scope>/<name>/<name>.component.{ts,html,css}` (Datei-Triple).
- Generator-Pin: `kind: llm`, `provider/model/prompt_version=0.1.0`, `cache_key` deterministisch.
- `render_for_target` Dispatcher um `target == "angular"` erweitern.
- Inputs → `@Input()`, Outputs → `@Output() EventEmitter`, Events → Click-Handler im Template (Prompt-Vorgabe an LLM).
- Replay-Fixtures unter `tests/fixtures/replay/angular/<cache_key>.json`.
- Golden Renders für alle 5 Specs in `tests/fixtures/golden/angular/org/<name>/...`.
- Tests: `core/tests/test_codegen_angular.py` (Determinismus via Replay, Golden-Match, Input/Output/Event-Binding).

## Stage 4: Conformance-Runner (Build-Smoke + Visual-Regression)

Outcome: `speccify conformance --target {react,swiftui,angular}` Command + CI-Job(s); pro Target wird das Render-Output gebaut (oder Source-only-Smoke), und falls die Spec `screenshots[]` hat, gegen Render-Output verglichen.

- `cli/src/speccify_cli/commands/conformance.py`: lädt Lockfile, ruft Renderer, führt pro Target Build-Smoke aus.
  - **React**: `npm run build` im Snapshot-Repo (Vite); Exit-Code = Conformance-Status.
  - **Angular**: `ng build` im Snapshot-Repo; ng-Workspace pre-generiert in `conformance/angular/`.
  - **SwiftUI**: nur Compile-Smoke via `swiftc -parse` (kein Xcode-Sim) — voll-interaktive Tests bleiben Phase 4.
- Visual-Regression: Spec-`screenshots[]` werden gelesen; pro Target wird ein Renderer-Output-Screenshot via headless-Tool erzeugt (React/Angular: Playwright; SwiftUI: snapshot-test-Lib) und gegen Spec-Screenshot pixel-vergleichen (Toleranz konfigurierbar).
- Conformance-Failures → Exit 1 mit strukturiertem Report (welches Target, welche Spec, welches Kriterium).
- CI: `.github/workflows/ci.yml` bekommt drei zusätzliche Jobs `conformance-react`, `conformance-angular`, `conformance-swiftui` (matrixed).
- Tests: `cli/tests/test_conformance.py` (Happy-Path pro Target, Drift-Detection, Visual-Regression-Toleranz).

## Stage 5: Workspaces — `workspaces: [...]` + globale MVS + Cargo-Style Root-Lockfile

Outcome: Ein Workspace-Root-Manifest mit `workspaces: ["packages/*"]` lockt/pullt/verifyt alle Member; **ein** zentrales `speccify.lock` im Root mit globaler MVS-Auflösung; ConflictError bei unvereinbaren Ranges zwischen Membern.

- `core/src/speccify_core/workspace.py`: `Workspace.load(root)` entdeckt Member-Manifeste (Glob), aggregiert Dependencies, ruft Resolver einmal mit allen Ranges; `ConflictError` enthält Source-Trace pro Member.
- `manifest.schema.json`: optionales `workspaces: [path/glob]` top-level.
- `cli/src/speccify_cli/commands/{lock,pull,verify}.py`: erkennen Workspace, iterieren über Member, schreiben **ein** Root-Lockfile.
- `speccify add` im Workspace-Root: hängt Dep an angegebenes Member-Manifest, locked global.
- Tests: `cli/tests/test_workspaces.py` (2-Member-Setup, Diamond über Member korrekt aufgelöst, Conflict-Error mit Source-Trace, `verify` schlägt fehl bei Drift in genau einem Member).
- `example-workspace/` Fixture mit zwei Members für E2E-Smoke.

## Stage 6: Cross-Consistency-Erweiterung CLI ↔ MCP ↔ Web auf alle 3 Targets

Outcome: Parametrierter Pytest-Test, der pro Target × (CLI, MCP, Web-Render-Endpoint) byte-identische Render-Outputs für die 5 Referenz-Specs liefert.

- `apps/web/backend/src/speccify_web_backend/services/render.py`: `render_spec_from_yaml` unterstützt `target`-Argument für alle 3 Targets.
- MCP-Tools (`render`, `pull`, `verify`) bekommen `target`-Parameter (target-agnostisch via Argument, Master-Plan-Linie).
- `tests/test_cross_consistency_targets.py` (Root): pytest-parametrize über `target ∈ {react, swiftui, angular}` × `spec ∈ 5 Referenz-Specs` × `route ∈ {cli, mcp, web}` → 75 Pfade, byte-identische Outputs.
- Update bestehender `apps/web/backend/tests/test_cross_consistency.py` + `registry/tests/test_cross_consistency_registry.py` auf Multi-Target.

## Stage 7: Smoke gegen Phase-2-Registry-Pfad mit Multi-Target

Outcome: `RemoteRegistry` + Resolver liefern für `targets: [react, swiftui]`-Manifest byte-identische Outputs wie Lokal-Setup; Lockfile v3 Round-Trip durchgehend.

- `registry/tests/test_remote_multi_target.py`: Publish einer Spec auf Live-Server, dann zwei-Target-`pull` via `RemoteRegistry`, Vergleich mit `LocalRegistry`-Path; beide Targets byte-identisch.
- Falls nötig: kleine Erweiterungen in `RemoteRegistry`/`Resolver` für Multi-Target-Lockfile-Eintrag.

## Stage 8: Master-Plan-Sync + AGENTS-Update + Phase-3-Archiv + Tag-Vorschlag `v0.6.0-phase-3`

Outcome: Phase 3 dokumentarisch abgeschlossen; Master-Plan reflektiert SwiftUI+Angular als zweites/drittes Target + Conformance-Runner-MVP + Workspaces; Phase-4-Skelett-Hinweis im Master-Plan.

- `.agent/plans/speccify-plan.md`: Phase-3-Abschluss-Block analog zu Phase-2-Block; Workspaces-Tabelle aus Phase 3 in Phase 4 weiterführen falls nötig.
- `AGENTS.md` „Aktuelle Phase" auf Phase 3 done + Phase-4-Plan-Skelett verweisen.
- `.agent/status.md` aktualisieren.
- Phase-3-Plan archivieren nach `.agent/plans/archive/phase-3-codegen-targets.md`.
- Tag-Vorschlag an User: **`v0.6.0-phase-3`** (selbst nicht setzen, vgl. `.agent/rules.md`).


# Status Tracker

| Stage | Outcome | Status |
|---|---|---|
| 0 | Open Questions geklärt, Decisions dokumentiert, Round-2-Delivery-Steps geschrieben. | **Done (2026-05-24)** |
| 1 | Codegen-Abstraktion + Lockfile-Schema-Bump v3. | Open |
| 2 | SwiftUI-Renderer + Golden Renders. | Open |
| 3 | Angular-Renderer + Golden Renders. | Open |
| 4 | Conformance-Runner (Build-Smoke + Visual-Regression) + CI-Jobs. | Open |
| 5 | Workspaces (Cargo-Stil Root-Lockfile + globale MVS). | Open |
| 6 | Cross-Consistency CLI ↔ MCP ↔ Web auf alle 3 Targets. | Open |
| 7 | Smoke gegen Phase-2-Registry-Pfad mit Multi-Target. | Open |
| 8 | Master-Plan-Sync + Phase-3-Archiv + Tag-Vorschlag `v0.6.0-phase-3`. | Open |


# Risks & Mitigations

| Risiko | Wahrscheinlichkeit | Mitigation |
|---|---|---|
| **Conformance-Runner-Stack zu komplex** (z. B. Xcode-Simulator in Docker auf CI) | hoch | Stage 0 klärt pro Target realistische Harness-Optionen; Fallback ist „nur Snapshot-Vergleich + Build-Smoke" statt vollwertige Interaktions-Tests. |
| **Multi-Target-Manifest bricht Phase-1b-Pull-Semantik** | mittel | Lockfile-Schema-Bump (v2 → v3) mit Backward-Compat-Migration (analog Phase-2-v1→v2-Migration). Stage 0 entscheidet das Layout vor Code. |
| **Workspaces-Resolver-Diamonds über Member** | mittel | Stage 0 fixiert Semantik (global MVS vs. per-member); ConflictError mit Source-Trace bleibt aus Phase 1a. |
| **Cross-Consistency mit 3 Targets × CLI/MCP/Web wächst quadratisch** | mittel | Parametrierte Pytest-Tests statt N×M handgeschriebene Pfade. |
| **Determinismus von LLM-Targets** (alle 3 Targets sind `kind: llm`) | hoch | Replay-Cache-Pattern aus Phase 1b (`ReplayCacheClient` + `CacheKey`) wiederverwenden; Offline-Mode-CI-Job ist Pflicht; Replay-Fixtures pro Target in `tests/fixtures/replay/<target>/`. |
| **Phase-3-Scope explodiert** | hoch | Stage 0 entscheidet 2 vs. 3 Targets in Phase 3 (Frage 2); Workspaces kann notfalls in eine Phase 3a/3b geteilt werden. |
