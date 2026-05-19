# AGENTS.md — Onboarding für Coding-Agents

> Lies dieses Dokument zuerst. Es ist der Einstiegspunkt für jede Junie-/Claude-Code-/Cursor-Session in diesem Repo.

> Bitte beachte auch .agent/agent.md und die dort referenzierten Regeln. Und bleibe bitte im Bearbeitungsmodus.

## Vision

> *„npm für Spezifikationen statt für Code — Komponenten beschreiben, nicht implementieren. Der AI-Agent ist der Compiler in das Ziel-Framework."*

Speccify ist eine Spec-First-Plattform für sprach- und framework-unabhängige Komponenten-Spezifikationen. Eine `speccify.yaml`-Spec beschreibt Verhalten, Inputs/Outputs, Akzeptanzkriterien und visuelle Referenzen — und ein AI-Agent generiert daraus deterministisch Code für SwiftUI, React, Angular, Jetpack Compose oder andere Targets.

Langfristige Quelle der Wahrheit: [`.agent/plans/speccify-plan.md`](./.agent/plans/speccify-plan.md). Dieses Repo (nicht das ursprüngliche LambdaPy-Repo) ist ab jetzt die Single Source of Truth für Plan-Änderungen.

## Aktuelle Phase

**Phase 1d aktiv — Browser-Playground (`apps/web/`). Steps 0–5 abgeschlossen: FastAPI-Backend `speccify-web-backend` mit `/api/v1/specs` + `/api/v1/render` (offline gegen Replay-Cache), Next.js 15 / React 19 / TS-Frontend (pnpm) mit Spec-Picker, Monaco-YAML-Editor, Render-Output (TSX + `generator_pin`) und Error-Panel (`cache_miss`-Hint), **Cross-Consistency-Test CLI ↔ MCP ↔ Web byte-identisch grün** (`apps/web/backend/tests/test_cross_consistency.py`), **CI um zwei Jobs erweitert** (`apps/web backend (offline)` Pytest + `apps/web frontend build` pnpm `--frozen-lockfile`). **183 Pytest grün**, Frontend `pnpm build` grün (lokal verifiziert). Nächster Schritt: Step 6 — Wrap-up (`speccify-plan.md`-Sync + Tag-Vorschlag `v0.4.0-phase-1d`).**

Aktiver Plan: [`.agent/plans/phase-1d-browser-playground.md`](./.agent/plans/phase-1d-browser-playground.md) (Steps 0–5 abgeschlossen, Step 6 = Wrap-up ist der nächste Schritt). Archivierte Phasen-Pläne: [`archive/phase-1c-mcp-server.md`](./.agent/plans/archive/phase-1c-mcp-server.md) (Tag-Vorschlag `v0.3.0-phase-1c`), [`archive/phase-1b-react-codegen.md`](./.agent/plans/archive/phase-1b-react-codegen.md) (Tag `v0.2.0-phase-1b`), [`archive/phase-1a-resolver-lockfile.md`](./.agent/plans/archive/phase-1a-resolver-lockfile.md) (Tag `v0.1.0-phase-1a`).

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
