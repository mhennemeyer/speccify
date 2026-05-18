# Speccify

> npm für Spezifikationen statt für Code — Komponenten beschreiben, nicht implementieren.
> Der AI-Agent ist der Compiler in das Ziel-Framework.

Speccify ist eine Spec-First-Plattform für sprach- und framework-unabhängige Komponenten-Spezifikationen.
Eine `speccify.yaml`-Spec beschreibt Verhalten, Inputs/Outputs, Akzeptanzkriterien und visuelle Referenzen
einer Komponente — und ein AI-Agent generiert daraus deterministisch Code für SwiftUI, React, Angular,
Jetpack Compose oder andere Targets. Verteilung über CLI (`speccify`) und MCP-Server.

## Quickstart

```bash
uv sync --all-packages
uv run pytest
uv run ruff check .
```

### End-to-End Smoke (offline, ohne API-Key)

Setzt voraus, dass der eingecheckte Replay-Cache unter
`tests/fixtures/llm-cache/` aktuell ist (siehe unten).

```bash
# Im example-project:
cd example-project
uv run speccify lock
uv run speccify pull --offline --out ./out
uv run speccify verify --offline --out ./out

# Frisches Projekt von Grund auf:
uv run speccify init my-app --target react
cd my-app
uv run speccify add @org/button --registry ../registry-fixtures
uv run speccify lock --registry ../registry-fixtures
uv run speccify pull --offline --registry ../registry-fixtures \
  --cache-dir ../tests/fixtures/llm-cache --out ./out
uv run speccify verify --offline --registry ../registry-fixtures \
  --cache-dir ../tests/fixtures/llm-cache --out ./out
```

### Replay-Cache neu aufnehmen (Maintainer)

`speccify pull`/`verify` laufen in CI ausschließlich offline gegen den
eingecheckten Replay-Cache. Ändert sich eine Spec, der Prompt oder der
Modell-Pin, müssen die Cache-Einträge neu aufgenommen werden. Das geht
mit dem Maintainer-Skript:

```bash
# AWS-Credentials (Bedrock) müssen in der Umgebung bzw. in .env liegen.
uv sync --extra bedrock
uv run python scripts/record_llm_cache.py            # idempotent, skipt vorhandene Einträge
uv run python scripts/record_llm_cache.py --force    # überschreibt vorhandene Einträge
```

Das Skript läuft niemals in CI — es greift aufs Netz zu. Ergebnis sind
JSON-Einträge unter `tests/fixtures/llm-cache/`, die mit eingecheckt
werden.

## MCP-Server (`speccify-mcp`)

Speccify bringt einen MCP-Server mit, der Coding-Agents (Claude Code,
Junie, Cursor, Aider) denselben Workflow wie die CLI gibt — ohne dass
die Agents Spec-/Lockfile-Wissen mitbringen müssen. Tools spiegeln die
CLI-Subkommandos 1:1 (`resolve`, `lock`, `pull`, `verify`, `render`,
`lint`); zusätzlich gibt es Resources (`speccify://manifest`,
`speccify://lockfile`, `spec://{scope}/{name}@{version}`) und einen
`add-spec`-Prompt.

```json
{
  "mcpServers": {
    "speccify": {
      "command": "speccify-mcp",
      "args": ["--project", "."]
    }
  }
}
```

Details und der Smoke-Aufruf (`uv run python scripts/mcp_smoke.py`)
stehen in [`mcp/README.md`](./mcp/README.md).

## Wo es weitergeht

- [`AGENTS.md`](./AGENTS.md) — Onboarding für Coding-Agents (Vision, Repo-Layout, Konventionen).
- [`.agent/plans/speccify-plan.md`](./.agent/plans/speccify-plan.md) — Master-Plan (langfristige Vision & Roadmap).
- [`.agent/plans/phase-1c-mcp-server.md`](./.agent/plans/phase-1c-mcp-server.md) — Aktiver Plan: MCP-Server `speccify-mcp` (stdio).
- [`.agent/plans/phase-1b-react-codegen.md`](./.agent/plans/phase-1b-react-codegen.md) — Abgeschlossen: React-LLM-Codegen + Replay-Cache + `init`.
- [`.agent/plans/phase-1a-resolver-lockfile.md`](./.agent/plans/phase-1a-resolver-lockfile.md) — Abgeschlossen: Resolver + Lockfile + `add`/`pull`/`verify`.
- [`.agent/plans/archive/phase-0-wrap-up.md`](./.agent/plans/archive/phase-0-wrap-up.md) — Phase-0-Wrap-up (abgeschlossen, ADR-Light für Q1–Q5).
- [`.agent/plans/archive/phase-0-spec-schema-spike.md`](./.agent/plans/archive/phase-0-spec-schema-spike.md) — Phase-0-Implementierungs-Plan (abgeschlossen, archiviert).
- [`.agent/plans/archive/phase-1a0-rename-to-speccify.md`](./.agent/plans/archive/phase-1a0-rename-to-speccify.md) — Rebrand `flowcation` → `speccify` (abgeschlossen).

## Status

Phase 1c läuft (MCP-Server `speccify-mcp` über stdio: Tools, Resources, Prompts; offline-Smoke in CI).
Abgeschlossen: Phase 0 (Schema v0 + `speccify lint`, Tag `v0.0.0-phase0`),
Phase 1a-0 (Rebrand auf `speccify`, Tag `v0.0.1-speccify-rebrand`),
Phase 1a (Resolver + Lockfile + Stub-Codegen + `add`/`lock`/`pull`/`verify`, Tag `v0.1.0-phase-1a`),
Phase 1b (React-LLM-Codegen + Replay-Cache + `init`, Tag `v0.2.0-phase-1b`).

## Lizenz

MIT — siehe [`LICENSE`](./LICENSE).
