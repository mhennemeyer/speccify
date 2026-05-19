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

## Browser-Playground (`apps/web/`)

Neben CLI und MCP-Server gibt es einen Browser-Playground unter
`apps/web/` (Phase 1d). Frontend ist Next.js 15 / React 19 /
TypeScript, Backend ist FastAPI (in-process `speccify-core`). Der
Playground rendert eingecheckte Referenz-Specs **byte-identisch zur
CLI/MCP** — verifiziert per Cross-Consistency-Test
(`apps/web/backend/tests/test_cross_consistency.py`). Offline-only
gegen den eingecheckten Replay-Cache; kein Live-LLM.

```bash
# Terminal A:
uv run speccify-web-backend --host 127.0.0.1 --port 8000
# Terminal B:
cd apps/web/frontend && pnpm install && pnpm dev
```

Details: [`apps/web/README.md`](./apps/web/README.md).

## Wo es weitergeht

- [`AGENTS.md`](./AGENTS.md) — Onboarding für Coding-Agents (Vision, Repo-Layout, Konventionen).
- [`.agent/plans/speccify-plan.md`](./.agent/plans/speccify-plan.md) — Master-Plan (langfristige Vision & Roadmap).
- [`.agent/plans/phase-1d-browser-playground.md`](./.agent/plans/phase-1d-browser-playground.md) — Abgeschlossen (alle Steps): Browser-Playground (`apps/web/`); Archivierung nach User-Tag `v0.4.0-phase-1d`.
- [`.agent/plans/archive/phase-1c-mcp-server.md`](./.agent/plans/archive/phase-1c-mcp-server.md) — Abgeschlossen: MCP-Server `speccify-mcp` (stdio).
- [`.agent/plans/archive/phase-1b-react-codegen.md`](./.agent/plans/archive/phase-1b-react-codegen.md) — Abgeschlossen: React-LLM-Codegen + Replay-Cache + `init`.
- [`.agent/plans/archive/phase-1a-resolver-lockfile.md`](./.agent/plans/archive/phase-1a-resolver-lockfile.md) — Abgeschlossen: Resolver + Lockfile + `add`/`pull`/`verify`.
- [`.agent/plans/archive/phase-0-wrap-up.md`](./.agent/plans/archive/phase-0-wrap-up.md) — Phase-0-Wrap-up (abgeschlossen, ADR-Light für Q1–Q5).
- [`.agent/plans/archive/phase-0-spec-schema-spike.md`](./.agent/plans/archive/phase-0-spec-schema-spike.md) — Phase-0-Implementierungs-Plan (abgeschlossen, archiviert).
- [`.agent/plans/archive/phase-1a0-rename-to-speccify.md`](./.agent/plans/archive/phase-1a0-rename-to-speccify.md) — Rebrand `flowcation` → `speccify` (abgeschlossen).

## Status

Phase 1d **abgeschlossen** (Browser-Playground unter `apps/web/`: FastAPI-Backend + Next.js-Frontend, byte-identisch zu CLI/MCP via Cross-Consistency-Test; alle Steps 0–6 abgehakt, Tag-Vorschlag `v0.4.0-phase-1d`). Nächster Schritt: Phase-2-Plan-Entwurf (Registry-MVP).
Abgeschlossen: Phase 0 (Schema v0 + `speccify lint`, Tag `v0.0.0-phase0`),
Phase 1a-0 (Rebrand auf `speccify`, Tag `v0.0.1-speccify-rebrand`),
Phase 1a (Resolver + Lockfile + Stub-Codegen + `add`/`lock`/`pull`/`verify`, Tag `v0.1.0-phase-1a`),
Phase 1b (React-LLM-Codegen + Replay-Cache + `init`, Tag `v0.2.0-phase-1b`),
Phase 1c (MCP-Server `speccify-mcp` über stdio, Tag-Vorschlag `v0.3.0-phase-1c`),
Phase 1d (Browser-Playground `apps/web/`, Tag-Vorschlag `v0.4.0-phase-1d`).

## Lizenz

MIT — siehe [`LICENSE`](./LICENSE).
