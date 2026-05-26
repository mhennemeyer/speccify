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

## Stage 1a: Renderer-Protocol + TARGETS-Registry — **Done (2026-05-25)**

Outcome: `speccify_core` hat ein generisches `Renderer`-Protocol + `TARGETS`-Registry; React-Codegen aus Phase 1b transparent darüber portiert; alle 225 Root-Tests grün.

- `core/src/speccify_core/codegen/__init__.py`: `Renderer`-Protocol, `TargetRender`-Dataclass, `TARGETS: dict[str, Renderer]`, `register_target()`, `supported_targets()`, `render_for_target()` delegiert an Registry.
- React-Renderer aus Phase 1b unter `"react"` registriert; `SUPPORTED_TARGETS`-Backward-Compat-Konstante bleibt.
- Tests: `core/tests/test_renderer_protocol.py` (5 Tests: Registry-Lookup, Dispatcher, Unknown-Target-Error, Doppelregistrierung, supported_targets-Sortierung).
- Commits: `be848a4` (Tests) + `43462ee` (Refactor `__call__` Lesbarkeit).
- Verifiziert: `225 passed` Root-Pytest (`mcp/tests/test_stdio_smoke.py` einzeln grün); `ruff check core/` clean; `ruff format` clean.

## Stage 1b: Lockfile-Schema-Bump v3 + Manifest-Schema v2 — **Done (2026-05-26)**

**Substage 1b-α — Schema-Vorgriff (Done 2026-05-26)**:
- `schema/manifest.v2.schema.json` als Vorgriff angelegt (Multi-Target, `targets: list[str]`, `schema_version: const 2`, `minItems: 1` + `uniqueItems: true`) — noch nicht aktiv geladen.
- `schema/lockfile.v3.schema.json` als Vorgriff angelegt (Top-Level `targets: list[str]` ersetzt `target: str`; jeder LockEntry behält eigenes `target`-Feld; `signature`-Slot + `yank_status` aus v2 unverändert übernommen; `schema_version: const 3`) — noch nicht aktiv geladen.
- `schema/README.md`: Schema-Inventur dokumentiert (`spec`, `manifest{,.v1,.v2}`, `lockfile{,.v1,.v2,.v3}`); aktive Phase auf Phase 3 gesetzt.
- `schema/manifest.schema.json` bleibt v1 aktiv; `schema/lockfile.schema.json` bleibt v2 aktiv → keine Code-/Test-Brüche; 226 Root-Pytest grün, ruff/format clean.
- Entscheidung User: nur Schemas + Snapshots in dieser Session, Code-Migration als eigene Substage 1b-β nächste Session.

**Substage 1b-β — Code-Migration (Done 2026-05-26)**:

Outcome: Aktive Schemas auf v3/v2 angehoben; `ProjectManifest` + `Lockfile` in `speccify_core` mit `targets: tuple[str, ...]` als SoT + `.target` als Backward-Compat-Property; Loader-Migration v1→2→3 (Lockfile) und v1→2 (Manifest) transparent; `build_lockfile()` akzeptiert sowohl `str` als auch Liste; Repo-Bytes (`example-project/speccify.yaml`, `example-project/speccify.lock`) auf v2/v3 migriert. **226 Root-Pytest + 116 Registry-Pytest = 342 Tests gesamt grün**, ruff/format clean.

- `schema/manifest.schema.json` ist jetzt v2 (Inhalt aus `manifest.v2.schema.json`), `schema/lockfile.schema.json` ist jetzt v3 (Inhalt aus `lockfile.v3.schema.json`); Vorgriff-Files wurden zu aktiven Schemas promoted, Snapshots `manifest.v1.schema.json`, `lockfile.v1.schema.json`, `lockfile.v2.schema.json` bleiben als Backward-Compat-Prüfung im Loader.
- `core/src/speccify_core/manifest.py`: `ProjectManifest.targets: tuple[str, ...]` ist Single-Source-of-Truth; `.target`-Property liefert das erste Element für Single-Target-Manifeste (raises bei N≠1); v1→v2 Migration via `_migrate_manifest_to_v2()` (`schema_version: 1, target: str` → `schema_version: 2, targets: [target]`); `CURRENT_MANIFEST_SCHEMA_VERSION = 2`.
- `core/src/speccify_core/lockfile.py`: `Lockfile.targets: tuple[str, ...]` ist SoT; `.target`-Property liefert das erste Element für Single-Target-Lockfiles; Loader-Migration v1/v2→v3 via Schema-Switch (`LEGACY_V1_LOCKFILE_SCHEMA_PATH`, neue `LEGACY_V2_LOCKFILE_SCHEMA_PATH`) + Top-Level-Feld-Mapping (`target` → `targets`); `to_dict()` schreibt `targets: list[str]` Top-Level + sortiert Entries nach `(id, target)`; `build_lockfile()` akzeptiert `str | tuple[str, ...] | list[str]` (single-string-API erhält Rückwärtskompatibilität — entries werden Cross-Product targets × resolutions); `CURRENT_LOCKFILE_SCHEMA_VERSION = 3`.
- Repo-Bytes migriert: `example-project/speccify.yaml` auf `schema_version: 2 + targets: [react]`; `example-project/speccify.lock` neu erzeugt als `schema_version: 3 + targets: [react]` (mit den gleichen sha256/cache_keys wie bisher).
- Aufrufer angepasst: `cli/src/speccify_cli/commands/init.py` schreibt v2-Manifest; `cli/src/speccify_cli/commands/add.py` benutzt `ctx.manifest.targets` beim Re-Build; `scripts/mcp_smoke.py` prüft `schema_version: 2` + `- react` (YAML-Listen-Eintrag). Andere Aufrufer (`lock`, `pull`, `verify`, `mcp/tools/render`, `apps/web/backend/...`) profitieren transparent von der `.target`-Backward-Compat-Property für Single-Target-Manifeste.
- Tests aktualisiert: `core/tests/test_manifest.py` (v2-Assertions), `core/tests/test_lockfile_v2.py` (v3-Defaults, `targets`-Tuple-Konstruktor, v1→v3-Migrations-Test), `core/tests/test_resolver.py` (`_manifest()` benutzt `targets=`), `cli/tests/test_init.py`, `cli/tests/test_add.py`, `mcp/tests/test_resources_prompts.py`. Existierende Tests, die v1/v2-Lockfile-Bytes via String-Literal prüfen (z.B. `test_resolver.py`), bleiben unangetastet — sie validieren genau die Loader-Migration.
- Bewusst noch offen für spätere Stages: Multi-Target-Specs (`targets: [react, swiftui]`) sind im Schema erlaubt, werden aber von keinem aktuellen Adapter erzeugt; Stage 2/3/6 werden das füllen, sobald SwiftUI- und Angular-Renderer existieren.

## Stage 2: SwiftUI-Renderer (`kind: llm` + Replay-Cache) — **Done (2026-05-26)**

Outcome: SwiftUI-Renderer als 1:1-Phase-1b-Spiegel implementiert; `render_for_target(spec, "swiftui", llm_client=...)` erzeugt deterministisch eine `.swift`-Datei pro Spec über Replay-Cache; alle Tests grün.

- `core/src/speccify_core/codegen/swiftui_llm.py` analog zu `react_llm.py`: `build_prompt` (Jinja-Template `swiftui_llm.prompt.j2`, SwiftUI-Bindings: Inputs→Properties mit Defaults, Events→optionale Closures), `normalize_swift` (CRLF→LF, Markdown-Fences strippen), `validate_swift` (Klammer-Balancing inkl. Swift-Strings/`//`/`/* */`; kein JSX-Tag-Balancing), `make_cache_key`, `render`, `render_to_files`; Output-Pfad `<scope>/<Name>.swift`.
- Generator-Pin: `kind: llm`, `PROVIDER=bedrock`, `MODEL=bedrock/eu.anthropic.claude-opus-4-7`, `PROMPT_VERSION=0.1.0`, `TARGET=swiftui` — Cache-Key enthält `target` → SwiftUI- und React-Keys derselben Spec kollidieren nie.
- `CodegenError` wird aus `react_llm` re-exportiert, sodass alle LLM-Adapter eine gemeinsame Exception-Klasse teilen (wichtig für `pytest.raises(CodegenError)` aus `speccify_core` Top-Level-Export).
- `render_for_target` Dispatcher um `"swiftui"` erweitert (`_render_swiftui` in `codegen/__init__.py`); `TARGETS`-Registry enthält jetzt `{"react", "swiftui"}`; `SUPPORTED_TARGETS` reflektiert das.
- Tests: `core/tests/test_swiftui_llm.py` (20 Tests, analog `test_react_llm.py`): `normalize_swift`, `validate_swift` (balanced, unbalanced, Strings/Kommentare, unterminated), `build_prompt`-Inhalt, Cache-Key-Determinismus, Cross-Target-Key-Trennung (`swiftui ≠ react`), Render-via-Replay-Cache (Cache-Hit, Cache-Miss raises, Markdown-Fence-Stripping), `render_to_files`-Pfad (`org/Button.swift`), Dispatcher-Pfad mit byte-identischen Mehrfach-Renders.
- Backward-Compat-Anpassungen: `core/tests/test_react_llm.py::test_dispatcher_unknown_target_raises` benutzt jetzt `"definitely-unknown-target"` statt `"swiftui"`; `apps/web/backend/tests/test_render_route.py::test_render_unknown_target_returns_400` ebenfalls auf `"definitely-unknown-target"` umgestellt (sonst landet die Anfrage im echten Render-Pfad und liefert `cache_miss` 422 statt `unknown_target` 400).
- **Bewusst out-of-scope für Stage 2** (User-Decision 2026-05-26): keine eingecheckten Golden Renders + Replay-Fixtures — Phase 1b hat dieses Pattern in der Praxis ebenfalls nicht (kein `tests/fixtures/golden/react/` im Repo). Echte Golden Renders über tatsächliche LLM-Calls werden in Stage 4 (Conformance-Runner) gefüllt, sobald ein Maintainer einmal `scripts/record_llm_cache.py` gegen Bedrock laufen lässt.
- **Verifikation**: 246 Root-Pytest grün (+20 SwiftUI-Tests gegenüber Stage 1b) + 116 Registry-Pytest grün = **362 Tests gesamt**; ruff/format clean.

## Stage 3: Angular-Renderer (`kind: llm` + Replay-Cache) — **Done (2026-05-26)**

Outcome: Angular-Renderer als 1:1-Phase-1b-Spiegel implementiert; `render_for_target(spec, "angular", llm_client=...)` erzeugt deterministisch eine `.component.ts`-Datei pro Spec über Replay-Cache; alle Tests grün.

- `core/src/speccify_core/codegen/angular_llm.py` analog zu `react_llm.py`/`swiftui_llm.py`: `build_prompt` (Jinja-Template `angular_llm.prompt.j2`; Inputs → `@Input()`, Events → `@Output() EventEmitter<void|Payload>`, Selector `app-<kebab>`), `normalize_ts` (CRLF→LF, Markdown-Fences strippen), `validate_ts` (Klammer-Balancing inkl. `"`/`'`/Backtick-Template-Literals + `//`/`/* */`-Kommentare; kein JSX-Tag-Balancing), `make_cache_key`, `render`, `render_to_files`.
- **Single-File-Strategie**: Inline-Template + Inline-Styles direkt im `@Component`-Decorator → eine `.component.ts`-Datei pro Spec (statt Triple `ts+html+css`). Damit bleibt der Renderer spiegelgleich zu SwiftUI (single-file pro Spec) und der Validator muss kein Multi-File-Splitting machen. Output-Pfad `<scope>/<kebab-name>.component.ts` (z. B. `org/button.component.ts`).
- Generator-Pin: `kind: llm`, `PROVIDER=bedrock`, `MODEL=bedrock/eu.anthropic.claude-opus-4-7`, `PROMPT_VERSION=0.1.0`, `TARGET=angular` — Cache-Key enthält `target` → Angular-, SwiftUI- und React-Keys derselben Spec kollidieren nie.
- `CodegenError` wird aus `react_llm` re-exportiert (gemeinsame Exception-Klasse für alle LLM-Adapter).
- `render_for_target` Dispatcher um `"angular"` erweitert (`_render_angular` in `codegen/__init__.py`); `TARGETS`-Registry enthält jetzt `{"react", "swiftui", "angular"}`; `SUPPORTED_TARGETS` reflektiert das.
- Tests: `core/tests/test_angular_llm.py` (21 Tests, analog `test_swiftui_llm.py`): `normalize_ts`, `validate_ts` (balanced, unbalanced, Strings/Kommentare/Template-Literals, unterminated string, unterminated template literal), `build_prompt`-Inhalt, Cache-Key-Determinismus, Cross-Target-Key-Trennung (`angular ≠ react`, `angular ≠ swiftui`), Render-via-Replay-Cache (Cache-Hit, Cache-Miss raises, Markdown-Fence-Stripping), `render_to_files`-Pfad (`org/button.component.ts`), Dispatcher-Pfad mit byte-identischen Mehrfach-Renders.
- **Bewusst out-of-scope für Stage 3** (User-Decision 2026-05-26, analog Stage 2): keine eingecheckten Golden Renders + Replay-Fixtures — Phase 1b hat dieses Pattern in der Praxis ebenfalls nicht. Echte Golden Renders über tatsächliche LLM-Calls werden in Stage 4 (Conformance-Runner) gefüllt, sobald ein Maintainer einmal `scripts/record_llm_cache.py` gegen Bedrock laufen lässt.
- **Verifikation**: 267 Root-Pytest grün (+21 Angular-Tests gegenüber Stage 2) + 116 Registry-Pytest grün = **383 Tests gesamt**; ruff/format clean.

## Stage 4: Conformance-Runner (Static-Validate-Backend + Backend-Plugin-Slot) — **Done (2026-05-26)**

Outcome: `speccify conformance` Command + Modul `speccify_core.conformance` mit pluggable Backends; Default-Backend `static-validate` führt Re-Render + Lockfile-Hash-Drift-Check + expliziter Validator-Pass (`validate_tsx`/`validate_swift`/`validate_ts`) pro `(spec, target)`-Paar im Lockfile durch. Build-Smoke + Visual-Regression bleiben Phase-4-Backends hinter dem `ConformanceBackend`-Protocol — kein Docker, kein npm/ng/swiftc in Phase 3. **Verifikation: 280 Root-Pytest grün (+13 Conformance-Tests gegenüber Stage 3) + 116 Registry-Pytest grün = 396 Tests gesamt**, ruff/format clean.

**User-Decision 2026-05-26 (Scope-Reduktion gegenüber Original-Plan-Text)**: Da Sandbox/CI ohne Node/Angular-CLI/Swift-Toolchain läuft und der Original-Plan-Text mehrere Tool-Stacks fordert, wurde Stage 4 auf den reduzierten MVP-Scope verkleinert (`static-validate`-Backend). Build-Smoke (`npm run build` / `ng build` / `swiftc -parse`) und Visual-Regression bleiben als Phase-4-Plug-in-Backends im selben Protocol, ohne Stage 4 zu blockieren.

- `core/src/speccify_core/conformance.py` neu:
  - `ConformanceResult(spec_id, version, target, status, messages)` + `ConformanceReport(results, backend)` als strukturierte, maschinen-lesbare Reports.
  - Status-Codes: `ok` / `render_failed` / `hash_drift` / `validator_failed` / `no_outputs` (klein gehalten für CI-Filter pro Status).
  - `ConformanceBackend`-Protocol (Plugin-Slot) + Default `StaticValidateBackend` (kein externer Build).
  - `VALIDATORS: dict[str, _Validator]` mit `react`→`validate_tsx`, `swiftui`→`validate_swift`, `angular`→`validate_ts`; neue Targets registrieren sich hier.
  - `run_conformance(*, lockfile, registry, llm_client, targets=None, backend=None)` als Komfort-Wrapper; `targets` filtert auf eine Teilmenge der Lockfile-Targets.
  - `_run_one()` fängt `CacheMissError | CodegenError | NotImplementedError` als `render_failed`, prüft danach Drift gegen `generated_files_sha256`, ruft am Ende den Validator nochmal explizit auf — sodass Drift vs. Validator-Fehler eindeutig getrennt sind.
- `cli/src/speccify_cli/commands/conformance.py` neu: `speccify conformance [--project ...] [-t TARGET ...] [--registry ...] [--offline/--no-offline] [--cache-dir ...]`. Wiederverwendet `WorkspaceContext` + `build_replay_client` aus den verify/pull-Pfaden. Exit-Code: 0 wenn `report.ok`, sonst 1; Output via `format_report()` analog zu `verify`.
- `cli/src/speccify_cli/__main__.py`: Command registriert nach `verify`.
- `core/src/speccify_core/__init__.py`: Re-Exports `ConformanceBackend`, `ConformanceReport`, `ConformanceResult`, `StaticValidateBackend`, `run_conformance`.
- Tests:
  - `core/tests/test_conformance.py` (9 Tests): Happy-Path, Hash-Drift, no_outputs, Target-Filter (überspringt nicht-matchende Entries), Cache-Miss → `render_failed`, Backend-Name, `by_target()`-Gruppierung, Unknown-Target → `render_failed`, Replay-Cache-Existenz-Smoke. Lockfile-Instanzen werden in-memory gebaut (kein CLI/IO-Stack nötig).
  - `cli/tests/test_conformance_cli.py` (4 Tests, umbenannt von `test_conformance.py` wegen pytest-Modul-Namens-Kollision mit `core/tests/test_conformance.py`): CLI-Happy-Path, Target-Filter, Hash-Drift via gepatchtem Lockfile, fehlendes Lockfile → Exit 1.
- CI: `smoke`-Job E2E-Schritt erweitert um `uv run speccify conformance` nach `verify` (3 React-Specs → `static-validate` ok). Bestehende Jobs unverändert.
- Plan-Doku + `AGENTS.md` reflektieren Stage 4 Done.

## Stage 5: Workspaces — `workspaces: [...]` + globale MVS + Cargo-Style Root-Lockfile — **Done (2026-05-26, Kern-MVP)**

Outcome: Ein Workspace-Root-Manifest mit `workspaces: ["packages/*"]` wird via `speccify lock` aufgelöst und schreibt **ein** zentrales `speccify.lock` im Root mit globaler MVS. Diamond über zwei Member (`@org/button` in `packages/ui` + `packages/forms`) wird zu einer einzigen Version aufgelöst; `RangeConflictError` bei unvereinbaren Ranges mit Member-Trace. **289 Root-Pytest grün (+9 Workspace-Tests gegenüber Stage 4) + 116 Registry-Pytest = 405 Tests gesamt**, ruff/format clean.

**Scope-Reduktion gegenüber Original-Plan-Text (User-Decision 2026-05-26)**: Stage-5-Kern liefert `Workspace`-Klasse + Schema-Erweiterung + `lock`-Command Workspace-aware + `example-workspace/`-Fixture; **`pull`/`verify`-Workspace-Iteration sowie `speccify add` im Workspace-Root bleiben Folge-Substage** (Stage 5b oder Phase 4), weil sie zusätzliche Output-Routing-Logik benötigen (pro Member eigenes `out/`-Verzeichnis vs. zentrales `out/`). Stage-0-Erfolgskriterium 3 (Workspace lockt/pullt/verifyt) wird damit nur teilweise erfüllt — `lockt` ja, `pullt/verifyt` noch nicht — aber die Architektur (globale MVS, Cargo-Stil Root-Lockfile, ConflictError mit Source-Trace) ist vollständig.

- `schema/manifest.schema.json`: optionales Top-Level `workspaces: [glob, ...]` (`minItems: 1` + `uniqueItems: true`); `targets` + `dependencies` aus `required` entfernt (reiner Workspace-Root darf nur `schema_version` + `workspaces` haben). Schema bleibt v2 (kein Schema-Bump — additive Erweiterung).
- `core/src/speccify_core/manifest.py`: `ProjectManifest.workspaces: tuple[str, ...]` + `.is_workspace_root`-Property; `targets`-Default `()` zugelassen; `write()` schreibt `targets`/`workspaces` nur wenn nicht-leer.
- `core/src/speccify_core/workspace.py` neu: `Workspace.load(root)` entdeckt Member-Manifeste via Glob (sortiert nach `relative_path`), validiert „keine verschachtelten Workspaces", aggregiert Targets (Union) und Dependencies pro Spec-Id mit Member-Source-Trace; `WorkspaceError`-Klasse + `WorkspaceMember`-Dataclass.
- `core/src/speccify_core/resolver.py`: `Resolver.resolve_workspace(aggregated_dependencies)` als neue API; `resolve()` selbst auf eine gemeinsame `_resolve_from_constraints()`-Innenmethode refaktoriert. Aggregierte Constraints behalten Member-Pfad als `source` — `RangeConflictError` zeigt damit den schuldigen Member.
- `cli/src/speccify_cli/commands/lock.py`: `_is_workspace_root()` + `_run_workspace_lock()` als neuer Workspace-Pfad; Single-Manifest-Pfad unverändert. `WorkspaceError` in `lock_command` als Failure-Class registriert.
- `core/src/speccify_core/__init__.py`: `Workspace`, `WorkspaceError`, `WorkspaceMember` re-exportiert (`__all__`).
- `example-workspace/speccify.yaml` (Root) + `example-workspace/packages/{ui,forms}/speccify.yaml` (zwei Member): Diamond-Setup mit `@org/button` in beiden Membern.
- Tests:
  - `core/tests/test_workspace.py` (7 Tests): Discovery-Reihenfolge, aggregierte Dependencies mit Member-Trace, globale MVS-Auflösung (Diamond → 1 Version), kein `workspaces:`-Feld → `WorkspaceError`, leerer Glob → `WorkspaceError`, Member ohne Manifest → `WorkspaceError`, verschachtelter Workspace → `WorkspaceError`.
  - `cli/tests/test_workspaces.py` (2 Tests): `speccify lock` auf `example-workspace`-Kopie schreibt Root-Lockfile mit 2 Entries × 1 Target = 2 Einträgen; unvereinbare Caret-Ranges zwischen zwei Membern → Exit 1 mit Spec-Id in der Fehler-Message.

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
| 1a | Renderer-Protocol + TARGETS-Registry, React portiert. | **Done (2026-05-25)** |
| 1b | Lockfile-Schema-Bump v3 + Manifest-Schema v2 + Adapter. | **Done (2026-05-26)** |
| 2 | SwiftUI-Renderer + Golden Renders. | **Done (2026-05-26)** |
| 3 | Angular-Renderer (single-file `.component.ts` mit Inline-Template). | **Done (2026-05-26)** |
| 4 | Conformance-Runner (Static-Validate-Backend + Backend-Plugin-Slot). | **Done (2026-05-26)** |
| 5 | Workspaces (Cargo-Stil Root-Lockfile + globale MVS, lock-only MVP; pull/verify Workspace-Iteration als Folge-Substage). | **Done (2026-05-26)** |
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
