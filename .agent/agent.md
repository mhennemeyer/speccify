Sprache: Deutsch
Ansprache: Du (nicht Sie)

In diesem Ordner befinden sich
    * Anweisungen für den AI-Agent
    * und Möglichkeiten zur Ablage von Informationen für den AI-Agent.

### Globale Regeln (via Symlink aus `~/.agent/`)
Die folgenden Dateien sind Symlinks auf `~/.agent/` und gelten projektübergreifend:
* `rules.md` – Coding-Standards, Architektur, Workflow, Commit-Strategie
* `functional.md` – FP-Regeln für Code-Generierung

## Vision

> *„npm für Spezifikationen statt für Code — Komponenten beschreiben, nicht implementieren. Der AI-Agent ist der Compiler in das Ziel-Framework."*

Speccify ist eine Spec-First-Plattform für sprach- und framework-unabhängige Komponenten-Spezifikationen. Eine `speccify.yaml`-Spec beschreibt Verhalten, Inputs/Outputs, Akzeptanzkriterien und visuelle Referenzen — und ein AI-Agent generiert daraus deterministisch Code für SwiftUI, React, Angular, Jetpack Compose oder andere Targets.

Langfristige Quelle der Wahrheit: [`.agent/plans/speccify-plan.md`](./.agent/plans/speccify-plan.md). Dieses Repo (nicht das ursprüngliche LambdaPy-Repo) ist ab jetzt die Single Source of Truth für Plan-Änderungen.

## Aktuelle Phase

**Phase 5c abgeschlossen (2026-05-29) — Visual-Regression-Skeleton produktiv.** Stage 0 hat 8 Open Questions vom User geklärt (Playwright + pixelmatch, React + Angular im Skeleton, 1 Referenz-PNG, 10 % Default-Tolerance, eigener CI-Workflow, kein `--update-snapshots`-Pytest-Flag im Skeleton, kein Schema-Bump für `screenshots[].tolerance` — beide vertagt auf Folge-Phase, Tag `v0.10.0-phase-5c`). Stages 1–4 geliefert: `VisualRegressionBackend` + `VisualDiffDriver`-Protocol + `VisualDiffResult`-Dataclass in `core/src/speccify_core/conformance_visual.py` (393 LOC); `PlaywrightPixelmatchDriver` für React + Angular via headless Chromium + Node-`pixelmatch`+`pngjs` (gepinnt: `playwright@1.44.0`, `pixelmatch@5.3.0`, `pngjs@7.0.0`); Pytest-Marker `visual_regression` in `pyproject.toml` mit Default-Exclude (`addopts = -m "not conformance and not visual_regression"`); Unit-Tests via Fake-Driver in `core/tests/test_conformance_visual.py` (13 Tests, decken Factory/Protocol/Tolerance/Toolchain-Missing/Reference-Missing-Pfade); E2E-Test `test_visual_regression_button_react` mit Skip-Strategie für fehlendes Chromium-Install; CI-Workflow `.github/workflows/visual-regression.yml` (Ubuntu, Node 20, Playwright-Browser-Cache, Path-Filter, Nightly-Cron `17 4 * * *`); `docs/visual-regression.md` (146 LOC) + Cross-Link + Scope-Tabelle in `docs/conformance.md` + README-Update; Plan archiviert nach `.agent/plans/archive/phase-5c-visual-regression-skeleton.md`. Referenz-PNG (`specs/screenshots/button-primary.png`) bleibt Maintainer-Hoheit — das Verzeichnis hat einen README mit Workflow; bis dahin skippt der E2E-Test sauber. **Verifikation: 346 Root-Pytest Default + 134 Registry-Pytest = 480 Tests grün** (+14 ggü. Phase 5b = 466); ruff/format clean; 1 `visual_regression`-E2E korrekt deselected. **Tag-Vorschlag an User: `v0.10.0-phase-5c`** (selbst nicht gesetzt, vgl. `rules.md`). **Nächster Schritt: Phase-5d-Plan-Entwurf nach User-Tag** — Kandidaten: Volle Visual-Regression-Coverage (5 Specs × {react, angular} mit Referenz-PNG-Snapshots), echter Component-Mount-Renderer (statt `<pre>`-Sandbox), `--update-snapshots`-Pytest-Flag, Schema-Bump `screenshots[].tolerance`, SwiftUI-Visual-Regression via Xcode-UI-Tests.

**Phase 5b abgeschlossen (2026-05-29) — alle Stages 0–6 Done.** Highlights: target-aware Replay-Cache-Recorder (`scripts/record_llm_cache.py`, Stage 1); Replay-Cache-Fixtures für `5 Specs × {angular, swiftui}` durch User committed (Stage 2); echte parametrisierte Build-Smokes über alle 5 Phase-0-Specs × {Angular, SwiftUI} in `core/tests/test_conformance_build_smoke.py` (Stage 3, 11 `@conformance`-Tests); voller 75-Pfad-Cross-Consistency-Sweep in `registry/tests/test_cross_consistency_sweep.py` — Matrix `5 Specs × 3 Targets × 5 Pfade (Local/Remote/CLI/MCP/Web)` byte-identisch (Stage 4, 15 Parametrisierungen). Stage 5: kein CI-YAML-Change nötig — Sweep läuft automatisch im bestehenden `registry-backend`-Job; README + `docs/conformance.md` aktualisiert. Stage 6: Plan archiviert nach `.agent/plans/archive/phase-5b-conformance-sweep.md`. **Verifikation: 332 Root-Pytest Default + 134 Registry-Pytest = 466 Tests grün + 11 `@conformance`-Tests; ruff/format clean.** **Tag-Vorschlag an User: `v0.9.0-phase-5b`** (selbst nicht gesetzt, vgl. `rules.md`). **Nächster Schritt: Phase-5c-Plan-Entwurf nach User-Tag** — Kandidaten: Visual-Regression-Skeleton, echtes `ng build`, Web-Backend Workspace-aware.


**Phase 5a abgeschlossen (2026-05-27) — Conformance Build-Smoke produktiv für alle 3 Targets.** Stage 0 hat 10 Open Questions vom User mit "folge deinen Empfehlungen" geklärt (Toolchain-Pinning lokal, Conformance-Marker mit Default-Exclude, Speicherort in `core/`, `toolchain_missing` ≠ Failure). Stages 1–5 geliefert: `BuildSmokeBackend` + `ToolchainDriver`-Protocol in `core/src/speccify_core/conformance_build_smoke.py`; `ReactToolchainDriver` (`tsc --noEmit` mit gepinntem `typescript@5.4.5` + `@types/react@18.2.79` via `npm install` + lokales `node_modules/.bin/tsc`); `AngularToolchainDriver` analog mit `@angular/core@17.3.0` + `experimentalDecorators=true`; `SwiftUIToolchainDriver` via `xcrun --sdk macosx swiftc -typecheck` (macOS-only, Linux skippt sauber). Replay-Cache-Blocker für SwiftUI/Angular umgangen durch synthetische Mini-Snippets im E2E-Test (Phase-5a-Scope = Driver-Pfad; Cross-Spec×Cache-Coverage bleibt Phase-5b-Scope). CI: separater Workflow `.github/workflows/conformance.yml` mit 3 Jobs (`conformance-react`/`-angular` auf Ubuntu+Node 20, `conformance-swiftui` auf macOS-latest); Trigger Path-Filter + Nightly-Cron `17 3 * * *` + `workflow_dispatch`. Default-CI (`ci.yml`) unverändert. `docs/conformance.md` (122 LOC) + README-Update + Plan-Archivierung. **Verifikation: 325 Root-Pytest (Default, `-m "not conformance"`) + 119 Registry-Pytest = 444 Tests gesamt grün; 3 `@conformance`-E2E-Tests passed in 6.17s lokal** (React/Angular/SwiftUI); ruff/format clean. **Tag-Vorschlag an User: `v0.8.0-phase-5a`** (selbst nicht gesetzt, vgl. `rules.md`). **Nächster Schritt: Phase-5b-Plan-Entwurf nach User-Tag** — Cache-Recording für SwiftUI/Angular, 75-Pfad-Cross-Consistency-Sweep, Visual-Regression, echtes `ng build`.

**Phase 4 abgeschlossen (2026-05-27) — Cargo-Style Workspaces produktiv.** Stage 0 hat 10 Open Questions geklärt (Root-only Lockfile, sichtbares `<member>/speccify_generated/`, CWD-Detection für `add`, strikte MVS-Konflikt-Strategie, keine Cross-Member-Path-Deps, Hash-only Verify, MCP-`workspace_root`-Bridge, Web-Backend out-of-scope, kein Schema-Bump, `workspaces:`-Key-Heuristik). Stages 1–8 geliefert: `Workspace.lock(registry) -> Lockfile` in `core/`, CLI `lock`/`pull`/`add --member`/`verify` workspace-aware (Pull materialisiert pro Member nach `<member>/speccify_generated/<target>/`, Verify ist Hash-only ohne Re-Render), `add --member/-m` mit CWD-Detection + automatischem Root-Re-Lock, diagnostische `ResolverError`-UX (Member-Pfade + Ranges + verfügbare Versionen) per Snapshot-Test gepinnt, MCP-Write-Tools (`lock`/`pull`/`verify`) mit optionalem `workspace_root`-Parameter (delegieren an die CLI-`run_*`-Funktionen → Single-Source-of-Truth), `docs/workspaces.md` (193 LOC) + README-Quickstart, Plan archiviert. **Verifikation: 312 Root-Pytest + 119 Registry-Pytest = 431 Tests gesamt grün** (+19 ggü. Phase 3 = 293), ruff/format clean. **Tag-Vorschlag an User: `v0.7.0-phase-4`** (selbst nicht gesetzt, vgl. `rules.md`). **Nächster Schritt: Phase-5-Plan-Entwurf nach User-Tag** — Kandidaten aus Phase-3-Folge-Substages: Conformance-Backends Build-Smoke + Visual-Regression, voller 75-Pfad-Cross-Consistency-Sweep mit echtem Bedrock-Replay-Cache für SwiftUI/Angular + fehlende Phase-0-Specs.

**Phase 3 abgeschlossen (2026-05-27) — Stages 0–8 Done.** Stage 7 hat den Registry-Pfad multi-target abgesichert: `registry/tests/test_remote_multi_target.py` (3 parametrisierte Tests) prüft pro `target ∈ {react, swiftui, angular}` byte-identische Outputs zwischen `LocalRegistry` und `RemoteRegistry` via `live_server`; React läuft gegen den eingecheckten LLM-Replay-Cache, SwiftUI/Angular gegen einen inline mit `ReplayCache.put()` + `make_cache_key()` befüllten `tmp_path`-Cache (analog Stage-6-Pattern). `RemoteRegistry` ist bereits in Phase 2 target-agnostisch implementiert — keine API-Änderungen nötig. Side-Quest: `core/pyproject.toml` `[tool.hatch.build.targets.wheel.force-include]` entfernt (force-include schattete den editable-Pfad), Templates werden jetzt über das normale `packages`-Setup mit eingebaut. **Verifikation: 293 Root-Pytest + 119 Registry-Pytest = 412 Tests gesamt grün** (+3 ggü. Stage 6), ruff/format clean. Stage 8 = Plan-Archivierung + AGENTS-/Status-Update; **Tag-Vorschlag an User: `v0.6.0-phase-3`** (selbst nicht gesetzt, vgl. `rules.md`). **Nächster Schritt: Phase-4-Plan-Entwurf nach User-Tag** (Phase-3-Folge-Substages bekannt: Workspace `pull`/`verify`/`add`-Iteration, Build-Smoke- + Visual-Regression-Conformance-Backends, voller 75-Pfad-Cross-Consistency-Sweep mit echtem Bedrock-Replay-Cache für SwiftUI/Angular + die fehlenden Phase-0-Specs).

**Phase 2 abgeschlossen — Registry-MVP (`registry/`).** Django-5-Backend `speccify-registry` (uv-Workspace-Member) mit REST-API unter `/api/v1/registry/...` für **Publish/Fetch/Versions/Search/Yank/Whoami/Tokens/Device-Code**, Django-Templates-Web-UI (Auth-Flow + Browse-Ansichten), Auth-Stack (Bearer-Tokens argon2 + Token-Prefix-Lookup, TOTP-2FA via `django-otp`, Device-Code-Login `gh auth login`-Stil). **Lockfile-Schema v2** (`yank_status` + `signature`-Slot, v1-Kompat). **Resolver-Multi-Registry** (`Registry`-Protocol + neue `RemoteRegistry` mit httpx + File-Cache + Server-Hash-Verify; pro `@scope` registry-gebunden via `ScopeRegistryConflictError` als Dependency-Confusion-Schutz). CLI-Erweiterungen `speccify login`/`whoami`/`publish`/`yank`; MCP-Tools `publish` + `yank` (Tool-Count 6→8). **Cross-Consistency erweitert** auf den Registry-Pfad (`registry/tests/test_cross_consistency_registry.py`: `LocalRegistry` ↔ `RemoteRegistry` via `live_server` byte-identisch). **CI**-Job `registry backend (django + postgres)` neu mit Postgres-16-Service-Container; bestehende Jobs unverändert. **Verifikation: 220 Root-Pytest grün, 116 Registry-Pytest grün → 336 Tests gesamt**; ruff/format clean. **Tag-Vorschlag an User: `v0.5.0-phase-2`** (selbst nicht gesetzt, vgl. `rules.md`). **Nächster Schritt: Phase 3 (zweites + drittes Codegen-Target + Conformance-Runner + Workspaces) — Plan-Entwurf nach User-Tag.**

Kein aktiver Plan in `.agent/plans/` (außer Master-Plan); Phase-5c-Plan archiviert: [`archive/phase-5c-visual-regression-skeleton.md`](./.agent/plans/archive/phase-5c-visual-regression-skeleton.md) (Tag-Vorschlag `v0.10.0-phase-5c`); Phase-5b-Plan archiviert: [`archive/phase-5b-conformance-sweep.md`](./.agent/plans/archive/phase-5b-conformance-sweep.md) (Tag-Vorschlag `v0.9.0-phase-5b`); Phase-5a-Plan archiviert: [`archive/phase-5a-conformance-backends.md`](./.agent/plans/archive/phase-5a-conformance-backends.md) (Tag-Vorschlag `v0.8.0-phase-5a`); Phase-4-Plan archiviert: [`archive/phase-4-workspaces.md`](./.agent/plans/archive/phase-4-workspaces.md) (Tag-Vorschlag `v0.7.0-phase-4`); Phase-3-Plan archiviert: [`archive/phase-3-codegen-targets.md`](./.agent/plans/archive/phase-3-codegen-targets.md) (Tag-Vorschlag `v0.6.0-phase-3`), [`archive/phase-2-registry-mvp.md`](./.agent/plans/archive/phase-2-registry-mvp.md) (Tag-Vorschlag `v0.5.0-phase-2`), [`archive/phase-1d-browser-playground.md`](./.agent/plans/archive/phase-1d-browser-playground.md) (Tag-Vorschlag `v0.4.0-phase-1d`), [`archive/phase-1c-mcp-server.md`](./.agent/plans/archive/phase-1c-mcp-server.md) (Tag-Vorschlag `v0.3.0-phase-1c`), [`archive/phase-1b-react-codegen.md`](./.agent/plans/archive/phase-1b-react-codegen.md) (Tag `v0.2.0-phase-1b`), [`archive/phase-1a-resolver-lockfile.md`](./.agent/plans/archive/phase-1a-resolver-lockfile.md) (Tag `v0.1.0-phase-1a`).

Phase 0 abgeschlossen (Tag `v0.0.0-phase0`): Schema v0, `speccify lint`, 5 Referenz-Specs. Phase 1a-0 (Rebrand `flowcation` → `speccify`, Tag `v0.0.1-speccify-rebrand`) ebenfalls abgeschlossen. Archiviert: [`phase-0-spec-schema-spike.md`](./.agent/plans/archive/phase-0-spec-schema-spike.md), [`phase-0-wrap-up.md`](./.agent/plans/archive/phase-0-wrap-up.md), [`phase-1a0-rename-to-speccify.md`](./.agent/plans/archive/phase-1a0-rename-to-speccify.md).

## Repo-Layout

| Pfad | Zweck | Aktiv ab Phase |
|---|---|---|
| `.agent/plans/` | Master-Plan + Phasen-Pläne | laufend |
| `core/` | `speccify-core` — geteilter Spec-Loader, Schema-Validator, Resolver, Codegen | 0 (Loader/Validator) / 1 (Rest) |
| `cli/` | `speccify-cli` — `speccify lint`, später `init`/`add`/`pull`/`lock`/`verify`/`publish` | 0 (`lint`) / 1 (Rest) |
| `mcp/` | `speccify-mcp` — MCP-Server für Coding-Agents | 1 |
| `schema/` | JSON-Schema-Dateien (kein Python-Paket) | 0 |
| `specs/` | Referenz-Specs als YAML | 0 |
| `codegen/` | Target-Adapter (zuerst SwiftUI) | 1 |
| `registry/` | Django-Backend (Discovery, Publish, sigstore) | 2 |
| `apps/web/` | Website + Browser-Playground (Stack offen) | 1/2 |
| `docs/` | Architektur-/Format-Doku außerhalb der Plan-Dokumente | laufend |

## Tooling

- **Python 3.12+**
- **`uv`** als Package-Manager (uv-Workspaces; `uv.lock` ist eingecheckt)
- **`ruff`** als Linter/Formatter
- **`mypy`** als Type-Checker (initial nicht strict)
- **`pytest`** als Test-Runner

Voraussetzung: `uv` muss installiert sein (`brew install uv` oder <https://docs.astral.sh/uv/>).

### Quickstart

```bash
uv sync                    # Workspace + alle Sub-Pakete editable installieren
uv run pytest              # Tests
uv run ruff check .        # Lint
uv run ruff format .       # Format
```

## Konventionen

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.
- **Branches**: `main` ist Default; Feature-Branches `feat/<thema>`, Fixes `fix/<thema>`.
- **Spec-Identität**: `spec://<name>@<semver>` oder `@scope/<name>@<semver>`.
- **Manifest-Datei**: `speccify.yaml`.
- **Lockfile**: `speccify.lock` (Hashes pflicht + Generator-Pin + Output-Hashes).
- **CLI-Binary**: `speccify`.
- **Lizenz**: MIT.
- **EditorConfig**: 4-space Python, 2-space Rest, LF, final newline.

## Hinweise für AI-Agents

1. **Phasen-Disziplin**: Implementiere nichts außerhalb des aktuellen Phasen-Plans. Bei Scope-Änderungen zuerst den Master-Plan re-lesen und ggf. einen neuen Phasen-Plan vorschlagen.
2. **Geparkte Bestandteile nicht antasten**: Tauri/Desktop (Phase 4) ist on-hold. Ebenso visuelles Tooling (Phase 5+) und Federation/Marketplace.
3. **Determinismus zuerst**: Spec-First, Code-Second. Wenn eine Aufgabe in Code beschreibbar ist, gehört sie wahrscheinlich in eine Spec.
4. **Resolver/Codegen wohnt in `core/`** — `cli/` und `mcp/` sind dünne Adapter darüber.
5. **Bei Unklarheiten** zur Roadmap: Master-Plan + Phasen-Plan checken; nicht raten.
6. **macOS-Tooling-Reibung**: `uv sync` triggert die Filesystem-Quarantäne und versteckt `.pth`-Dateien im venv. Ein Pytest-Session-Hook in `conftest.py` (Root + `registry/`) entversteckt sie automatisch via `scripts/_venv_hygiene.py`; manuell: `./scripts/fix-venv-hidden.sh` (mit `--deep` für versteckte Subdirs). Fehlende `.py`-Dateien (z. B. `django.contrib.admin.templatetags.admin_urls`) brauchen `uv sync --reinstall-package <name>`.
