# Speccify Browser-Playground (Phase 1d)

Demo-Oberfläche für die Speccify-Codegen-Pipeline. Frontend ist Next.js 15 /
React 19 / TypeScript, Backend ist FastAPI (in-process über `speccify-core`).
**Offline-only:** der Playground spielt ausschließlich gegen den eingecheckten
Replay-Cache (`tests/fixtures/llm-cache/`); kein Live-LLM, keine Bedrock-
Credentials im Browser.

## Stack

- **Frontend** (`apps/web/frontend/`) — Next.js 15 (App-Router), React 19,
  TypeScript strict, Monaco-Editor (`@monaco-editor/react`), zod für
  Response-Validierung. Paket-Manager: `pnpm` (>=10), Node >=22 LTS
  (`.nvmrc`).
- **Backend** (`apps/web/backend/`) — uv-Workspace-Member
  `speccify-web-backend`, FastAPI + Uvicorn, ruft direkt
  `speccify-core.render_for_target` mit `ReplayCacheClient(offline=True)`.

## Quickstart

```bash
# 1) Backend (Terminal A, im Repo-Root):
uv run speccify-web-backend --host 127.0.0.1 --port 8000

# 2) Frontend (Terminal B):
cd apps/web/frontend
pnpm install
pnpm dev          # http://localhost:3000
```

Der Next-Dev-Server proxied `/api/v1/*` automatisch auf
`http://localhost:8000` (siehe `next.config.ts`, override via
`SPECCIFY_BACKEND_URL`).

## Endpoints (v1)

- `GET /api/v1/specs` — Liste aus `<repo>/registry-fixtures/`
  (override via `SPECCIFY_REGISTRY_PATH`). Liefert pro `(scope, name)` die
  jeweils neueste Version mit `{id, version, title, yaml}`.
- `POST /api/v1/render` — Body `{spec_id, version, spec_yaml, target}`. Ruft
  `render_for_target` mit `ReplayCacheClient(offline=True)`. Antwort:
  `{spec_id, target, files, generator_pin}`.
- `GET /api/v1/health` — Smoke.

**Fehler-Codes:** `cache_miss` (422), `spec_invalid` (400), `unknown_target`
(400), `bad_request` (400). Selbe Codes wie CLI/MCP.

## Limitierungen (Phase 1d)

- Nur Target `react`.
- Nur Replay-Cache; editierte YAML ⇒ Cache-Miss (erwartetes Verhalten, UI
  erklärt es).
- Kein Deployment, kein Auth, keine Persistenz.

Master-Plan: [`.agent/plans/phase-1d-browser-playground.md`](../../.agent/plans/phase-1d-browser-playground.md).
