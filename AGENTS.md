# AGENTS.md — Onboarding für Coding-Agents

> Lies dieses Dokument zuerst. Es ist der Einstiegspunkt für jede Junie-/Claude-Code-/Cursor-Session in diesem Repo.

## Vision

> *„npm für Spezifikationen statt für Code — Komponenten beschreiben, nicht implementieren. Der AI-Agent ist der Compiler in das Ziel-Framework."*

Flowcation ist eine Spec-First-Plattform für sprach- und framework-unabhängige Komponenten-Spezifikationen. Eine `flowcation.yaml`-Spec beschreibt Verhalten, Inputs/Outputs, Akzeptanzkriterien und visuelle Referenzen — und ein AI-Agent generiert daraus deterministisch Code für SwiftUI, React, Angular, Jetpack Compose oder andere Targets.

Langfristige Quelle der Wahrheit: [`.agent/plans/flowcation-plan.md`](./.agent/plans/flowcation-plan.md). Dieses Repo (nicht das ursprüngliche LambdaPy-Repo) ist ab jetzt die Single Source of Truth für Plan-Änderungen.

## Aktuelle Phase

**Phase 1a — Resolver + Lockfile + `add`/`pull`/`verify` (Stub-Codegen).**

Aktiver Plan: [`.agent/plans/phase-1a-resolver-lockfile.md`](./.agent/plans/phase-1a-resolver-lockfile.md).

Phase 0 abgeschlossen (Tag `v0.0.0-phase0`): Schema v0, `flowcation lint`, 5 Referenz-Specs. Archiviert: [`phase-0-spec-schema-spike.md`](./.agent/plans/archive/phase-0-spec-schema-spike.md), [`phase-0-wrap-up.md`](./.agent/plans/archive/phase-0-wrap-up.md) (enthält ADR-Light Q1–Q5).

## Repo-Layout

| Pfad | Zweck | Aktiv ab Phase |
|---|---|---|
| `.agent/plans/` | Master-Plan + Phasen-Pläne | laufend |
| `core/` | `flowcation-core` — geteilter Spec-Loader, Schema-Validator, Resolver, Codegen | 0 (Loader/Validator) / 1 (Rest) |
| `cli/` | `flowcation-cli` — `flowcation lint`, später `init`/`add`/`pull`/`lock`/`verify`/`publish` | 0 (`lint`) / 1 (Rest) |
| `mcp/` | `flowcation-mcp` — MCP-Server für Coding-Agents | 1 |
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
- **Spec-Identität**: `flow://<name>@<semver>` oder `@scope/<name>@<semver>`.
- **Manifest-Datei**: `flowcation.yaml`.
- **Lockfile**: `flowcation.lock` (Hashes pflicht + Generator-Pin + Output-Hashes).
- **CLI-Binary**: `flowcation`.
- **Lizenz**: MIT.
- **EditorConfig**: 4-space Python, 2-space Rest, LF, final newline.

## Hinweise für AI-Agents

1. **Phasen-Disziplin**: Implementiere nichts außerhalb des aktuellen Phasen-Plans. Bei Scope-Änderungen zuerst den Master-Plan re-lesen und ggf. einen neuen Phasen-Plan vorschlagen.
2. **Geparkte Bestandteile nicht antasten**: Tauri/Desktop (Phase 4) ist on-hold. Ebenso visuelles Tooling (Phase 5+) und Federation/Marketplace.
3. **Determinismus zuerst**: Spec-First, Code-Second. Wenn eine Aufgabe in Code beschreibbar ist, gehört sie wahrscheinlich in eine Spec.
4. **Resolver/Codegen wohnt in `core/`** — `cli/` und `mcp/` sind dünne Adapter darüber.
5. **Bei Unklarheiten** zur Roadmap: Master-Plan + Phasen-Plan checken; nicht raten.
