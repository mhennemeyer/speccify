# AGENTS.md — Onboarding für Coding-Agents

> Lies dieses Dokument zuerst. Es ist der Einstiegspunkt für jede Junie-/Claude-Code-/Cursor-Session in diesem Repo.

> Bitte beachte auch .agent/agent.md und die dort referenzierten Regeln. Und bleibe bitte im Bearbeitungsmodus.

## Vision

> *„npm für Spezifikationen statt für Code — Komponenten beschreiben, nicht implementieren. Der AI-Agent ist der Compiler in das Ziel-Framework."*

Speccify ist eine Spec-First-Plattform für sprach- und framework-unabhängige Komponenten-Spezifikationen. Eine `speccify.yaml`-Spec beschreibt Verhalten, Inputs/Outputs, Akzeptanzkriterien und visuelle Referenzen — und ein AI-Agent generiert daraus deterministisch Code für SwiftUI, React, Angular, Jetpack Compose oder andere Targets.

Langfristige Quelle der Wahrheit: [`.agent/plans/speccify-plan.md`](./.agent/plans/speccify-plan.md). Dieses Repo (nicht das ursprüngliche LambdaPy-Repo) ist ab jetzt die Single Source of Truth für Plan-Änderungen.

## Aktuelle Phase

**Phase 3 aktiv — Stages 0 + 1a + 1b + 2 Done (2026-05-26).** Plan: [`.agent/plans/phase-3-codegen-targets.md`](./.agent/plans/phase-3-codegen-targets.md). Stage-0-Decisions: **SwiftUI + Angular** als zweites/drittes Target (beide in Phase 3); Conformance-Runner = **Build-Smoke + Snapshot + Visual-Regression gegen Spec-`screenshots[]`** (kein voll-interaktiver Stack — Phase 4); Workspaces = **Cargo-Stil Root-Lockfile + globale MVS**; Multi-Target = **`targets: []`-Liste im Manifest mit Lockfile-Schema-Bump v2→v3**; **alle neuen Targets `kind: llm` + Replay-Cache** (wie der reale React-Renderer aus Phase 1b, `react_llm.py` + `ReplayCacheClient`); Golden Renders unter `tests/fixtures/golden/<target>/...`; MCP-Tools **target-agnostisch via Argument** (Tool-Count bleibt 8). **Stage 1a Done**: `Renderer`-Protocol + `TARGETS`-Registry, React-Renderer transparent portiert, 225 Root-Pytest grün. **Stage 1b Done (2026-05-26, in zwei Substages 1b-α + 1b-β)**: aktive Schemas auf Lockfile-v3 + Manifest-v2 angehoben (Snapshots `manifest.v1`, `lockfile.v1`, `lockfile.v2` als Backward-Compat-Loader-Schemas erhalten); `ProjectManifest.targets: tuple[str, ...]` + `Lockfile.targets: tuple[str, ...]` sind Single-Source-of-Truth, `.target`-Property bleibt als Backward-Compat für Single-Target-Manifeste; In-Memory-Loader-Migration v1→v2 (Manifest) und v1/v2→v3 (Lockfile) transparent; `build_lockfile()` akzeptiert single-string + Liste (Cross-Product targets × resolutions); Repo-Bytes (`example-project/speccify.yaml`, `example-project/speccify.lock`) auf v2/v3 migriert; CLI-Aufrufer (`init`, `add`) + `scripts/mcp_smoke.py` + relevante Tests angepasst. **Stage 2 Done (2026-05-26)**: SwiftUI-Renderer als 1:1-Phase-1b-Spiegel (`swiftui_llm.py` + Jinja-Prompt + Swift-Validator + Dispatcher-Erweiterung `TARGETS={react, swiftui}`); `CodegenError` aus `react_llm` re-exportiert; Cache-Key enthält `target` → React/SwiftUI-Keys kollidieren nie. Bewusst out-of-scope (User-Decision): keine eingecheckten Golden Renders/Replay-Fixtures — Phase 1b hatte dieses Pattern in der Praxis ebenfalls nicht; echte LLM-Outputs werden in Stage 4 via `scripts/record_llm_cache.py` aufgenommen. **Verifikation: 246 Root-Pytest (+20 SwiftUI-Tests) + 116 Registry-Pytest = 362 Tests gesamt grün**, ruff/format clean. **Offene Stages 3–8**: Angular-Renderer → Conformance-Runner + CI → Workspaces → Cross-Consistency × 3 Targets → Registry-Path Multi-Target-Smoke → Master-Plan-Sync + Phase-3-Archiv + Tag-Vorschlag `v0.6.0-phase-3`.

**Phase 2 abgeschlossen — Registry-MVP (`registry/`).** Django-5-Backend `speccify-registry` (uv-Workspace-Member) mit REST-API unter `/api/v1/registry/...` für **Publish/Fetch/Versions/Search/Yank/Whoami/Tokens/Device-Code**, Django-Templates-Web-UI (Auth-Flow + Browse-Ansichten), Auth-Stack (Bearer-Tokens argon2 + Token-Prefix-Lookup, TOTP-2FA via `django-otp`, Device-Code-Login `gh auth login`-Stil). **Lockfile-Schema v2** (`yank_status` + `signature`-Slot, v1-Kompat). **Resolver-Multi-Registry** (`Registry`-Protocol + neue `RemoteRegistry` mit httpx + File-Cache + Server-Hash-Verify; pro `@scope` registry-gebunden via `ScopeRegistryConflictError` als Dependency-Confusion-Schutz). CLI-Erweiterungen `speccify login`/`whoami`/`publish`/`yank`; MCP-Tools `publish` + `yank` (Tool-Count 6→8). **Cross-Consistency erweitert** auf den Registry-Pfad (`registry/tests/test_cross_consistency_registry.py`: `LocalRegistry` ↔ `RemoteRegistry` via `live_server` byte-identisch). **CI**-Job `registry backend (django + postgres)` neu mit Postgres-16-Service-Container; bestehende Jobs unverändert. **Verifikation: 220 Root-Pytest grün, 116 Registry-Pytest grün → 336 Tests gesamt**; ruff/format clean. **Tag-Vorschlag an User: `v0.5.0-phase-2`** (selbst nicht gesetzt, vgl. `rules.md`). **Nächster Schritt: Phase 3 (zweites + drittes Codegen-Target + Conformance-Runner + Workspaces) — Plan-Entwurf nach User-Tag.**

Aktiver Plan: [`phase-3-codegen-targets.md`](./.agent/plans/phase-3-codegen-targets.md) (Stages 0 + 1a + 1b + 2 Done, Stages 3–8 Open; `isActive: true`); Tag-Vorschlag `v0.5.0-phase-2` für Phase 2 weiterhin offen an User (vgl. `.agent/rules.md`). Archivierte Phasen-Pläne: [`archive/phase-2-registry-mvp.md`](./.agent/plans/archive/phase-2-registry-mvp.md) (Tag-Vorschlag `v0.5.0-phase-2`), [`archive/phase-1d-browser-playground.md`](./.agent/plans/archive/phase-1d-browser-playground.md) (Tag-Vorschlag `v0.4.0-phase-1d`), [`archive/phase-1c-mcp-server.md`](./.agent/plans/archive/phase-1c-mcp-server.md) (Tag-Vorschlag `v0.3.0-phase-1c`), [`archive/phase-1b-react-codegen.md`](./.agent/plans/archive/phase-1b-react-codegen.md) (Tag `v0.2.0-phase-1b`), [`archive/phase-1a-resolver-lockfile.md`](./.agent/plans/archive/phase-1a-resolver-lockfile.md) (Tag `v0.1.0-phase-1a`).

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
