# AGENTS.md — Onboarding für Coding-Agents

> Lies dieses Dokument zuerst. Es ist der Einstiegspunkt für jede Junie-/Claude-Code-/Cursor-Session in diesem Repo.

> Bitte beachte auch .agent/agent.md und die dort referenzierten Regeln. Und bleibe bitte im Bearbeitungsmodus.

## Vision

> *„npm für Spezifikationen statt für Code — Komponenten beschreiben, nicht implementieren. Der AI-Agent ist der Compiler in das Ziel-Framework."*

Speccify ist eine Spec-First-Plattform für sprach- und framework-unabhängige Komponenten-Spezifikationen. Eine `speccify.yaml`-Spec beschreibt Verhalten, Inputs/Outputs, Akzeptanzkriterien und visuelle Referenzen — und ein AI-Agent generiert daraus deterministisch Code für SwiftUI, React, Angular, Jetpack Compose oder andere Targets.

Langfristige Quelle der Wahrheit: [`.agent/plans/speccify-plan.md`](./.agent/plans/speccify-plan.md). Dieses Repo (nicht das ursprüngliche LambdaPy-Repo) ist ab jetzt die Single Source of Truth für Plan-Änderungen.

## Aktuelle Phase

**Phase 3 abgeschlossen (2026-05-27) — Stages 0–8 Done.** Stage 7 hat den Registry-Pfad multi-target abgesichert: `registry/tests/test_remote_multi_target.py` (3 parametrisierte Tests) prüft pro `target ∈ {react, swiftui, angular}` byte-identische Outputs zwischen `LocalRegistry` und `RemoteRegistry` via `live_server`; React läuft gegen den eingecheckten LLM-Replay-Cache, SwiftUI/Angular gegen einen inline mit `ReplayCache.put()` + `make_cache_key()` befüllten `tmp_path`-Cache (analog Stage-6-Pattern). `RemoteRegistry` ist bereits in Phase 2 target-agnostisch implementiert — keine API-Änderungen nötig. Side-Quest: `core/pyproject.toml` `[tool.hatch.build.targets.wheel.force-include]` entfernt (force-include schattete den editable-Pfad), Templates werden jetzt über das normale `packages`-Setup mit eingebaut. **Verifikation: 293 Root-Pytest + 119 Registry-Pytest = 412 Tests gesamt grün** (+3 ggü. Stage 6), ruff/format clean. Stage 8 = Plan-Archivierung + AGENTS-/Status-Update; **Tag-Vorschlag an User: `v0.6.0-phase-3`** (selbst nicht gesetzt, vgl. `rules.md`). **Nächster Schritt: Phase-4-Plan-Entwurf nach User-Tag** (Phase-3-Folge-Substages bekannt: Workspace `pull`/`verify`/`add`-Iteration, Build-Smoke- + Visual-Regression-Conformance-Backends, voller 75-Pfad-Cross-Consistency-Sweep mit echtem Bedrock-Replay-Cache für SwiftUI/Angular + die fehlenden Phase-0-Specs).

**Phase 2 abgeschlossen — Registry-MVP (`registry/`).** Django-5-Backend `speccify-registry` (uv-Workspace-Member) mit REST-API unter `/api/v1/registry/...` für **Publish/Fetch/Versions/Search/Yank/Whoami/Tokens/Device-Code**, Django-Templates-Web-UI (Auth-Flow + Browse-Ansichten), Auth-Stack (Bearer-Tokens argon2 + Token-Prefix-Lookup, TOTP-2FA via `django-otp`, Device-Code-Login `gh auth login`-Stil). **Lockfile-Schema v2** (`yank_status` + `signature`-Slot, v1-Kompat). **Resolver-Multi-Registry** (`Registry`-Protocol + neue `RemoteRegistry` mit httpx + File-Cache + Server-Hash-Verify; pro `@scope` registry-gebunden via `ScopeRegistryConflictError` als Dependency-Confusion-Schutz). CLI-Erweiterungen `speccify login`/`whoami`/`publish`/`yank`; MCP-Tools `publish` + `yank` (Tool-Count 6→8). **Cross-Consistency erweitert** auf den Registry-Pfad (`registry/tests/test_cross_consistency_registry.py`: `LocalRegistry` ↔ `RemoteRegistry` via `live_server` byte-identisch). **CI**-Job `registry backend (django + postgres)` neu mit Postgres-16-Service-Container; bestehende Jobs unverändert. **Verifikation: 220 Root-Pytest grün, 116 Registry-Pytest grün → 336 Tests gesamt**; ruff/format clean. **Tag-Vorschlag an User: `v0.5.0-phase-2`** (selbst nicht gesetzt, vgl. `rules.md`). **Nächster Schritt: Phase 3 (zweites + drittes Codegen-Target + Conformance-Runner + Workspaces) — Plan-Entwurf nach User-Tag.**

Kein aktiver Plan in `.agent/plans/` (außer Master-Plan); Phase-3-Plan archiviert: [`archive/phase-3-codegen-targets.md`](./.agent/plans/archive/phase-3-codegen-targets.md) (Tag-Vorschlag `v0.6.0-phase-3`), [`archive/phase-2-registry-mvp.md`](./.agent/plans/archive/phase-2-registry-mvp.md) (Tag-Vorschlag `v0.5.0-phase-2`), [`archive/phase-1d-browser-playground.md`](./.agent/plans/archive/phase-1d-browser-playground.md) (Tag-Vorschlag `v0.4.0-phase-1d`), [`archive/phase-1c-mcp-server.md`](./.agent/plans/archive/phase-1c-mcp-server.md) (Tag-Vorschlag `v0.3.0-phase-1c`), [`archive/phase-1b-react-codegen.md`](./.agent/plans/archive/phase-1b-react-codegen.md) (Tag `v0.2.0-phase-1b`), [`archive/phase-1a-resolver-lockfile.md`](./.agent/plans/archive/phase-1a-resolver-lockfile.md) (Tag `v0.1.0-phase-1a`).

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
