# Speccify

> npm für Spezifikationen statt für Code — Komponenten beschreiben, nicht implementieren.
> Der AI-Agent ist der Compiler in das Ziel-Framework.

Speccify ist eine **vollständig quelloffene** Spec-First-Plattform für sprach- und framework-unabhängige
Komponenten-Spezifikationen. Eine `speccify.yaml`-Spec beschreibt Verhalten, Inputs/Outputs,
Akzeptanzkriterien und visuelle Referenzen einer Komponente — und ein AI-Agent generiert daraus
deterministisch Code für SwiftUI, React, Angular, Jetpack Compose oder andere Targets. Verteilung über
CLI (`speccify`) und MCP-Server; Specs werden über Git-Repos geteilt.

Aktuelle Richtung (siehe [Pivot-Plan](./.agent/plans/pivot-open-source-git-composer.md)):
formale, **mockbare Komponenten-APIs**, Komposition von Komponenten aus Unterkomponenten,
komplette Projekt-Builds aus Specs und ein **visueller Composer** auf Mock-Basis.

## Quickstart

```bash
uv sync --all-packages
uv run pytest
uv run ruff check .
```

### Lokaler Gesamt-Workflow (alle Services + Live-Codegen)

Ein Befehl fährt **das komplette System lokal** hoch — Playground-Backend +
-Frontend und die Marketing/Doku-Site:

```bash
./scripts/dev-up.sh                 # alles starten (Ctrl-C beendet alle)
./scripts/dev-up.sh --no-frontends  # nur Playground-Backend
```

| Service | URL |
|---|---|
| Playground-Backend (API) | <http://127.0.0.1:8000> |
| Playground-Frontend | <http://localhost:3000> |
| Marketing/Doku | <http://localhost:4321> |

Echte Code-Generierung aus einer Spec (auch für neue, selbst geschriebene
Specs) läuft jetzt über `speccify pull --no-offline` (Live-Bedrock bei
Cache-Miss, Ergebnis wird in den Replay-Cache geschrieben; Credentials aus
Umgebung/`.env`). Voller Walkthrough: [`docs/local-dev-e2e.md`](./docs/local-dev-e2e.md).

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

## Landingpage + Doku-Site (`apps/marketing/`)

Die öffentliche Landingpage und die durchsuchbare Doku-Site (Ziel-Domain
`speccify.io`) leben unter `apps/marketing/` (Phase 6). Stack ist
[Astro](https://astro.build) + [Starlight](https://starlight.astro.build),
Tailwind nur für die Landing-Routen. Geliefert: volle Tailwind-Landingpage
(Hero/Problem-Lösung/Demo/Targets/How-it-works/CTA), Playground-Iframe unter
`/try-it` (mit Fallback), aus Repo-`docs/` gespiegelte Doku und autogenerierte
CLI-Reference, Pagefind-Suche.

```bash
# Vom Repo-Root (pnpm-Workspace):
pnpm install
pnpm run marketing:dev      # http://localhost:4321
pnpm run marketing:build

# Doku-/CLI-Content (re-)generieren — CI bricht bei Drift via --check:
uv run python scripts/sync_docs_to_site.py   # docs/ → Site-MDX
uv run python scripts/gen_cli_docs.py        # speccify --help → CLI-Reference
```

Details: [`apps/marketing/README.md`](./apps/marketing/README.md) und
[`docs/deploy.md`](./docs/deploy.md) (Vercel-Setup + Env-Variablen).

## Troubleshooting: macOS-`UF_HIDDEN`-Workaround

macOS markiert von `uv` geschriebene `.pth`-Dateien in
`.venv/lib/python*/site-packages/` mit dem BSD-Flag `UF_HIDDEN`
(Filesystem-Quarantäne). Python's `site.py` ignoriert versteckte
`.pth`-Dateien, wodurch alle Workspace-Member (`speccify_cli`,
`speccify_mcp`, `speccify_web_backend`) nach jedem
`uv sync` plötzlich `ModuleNotFoundError` werfen.

Der Workaround läuft automatisch als Pytest-Session-Hook
(Root-`conftest.py`). Für manuelle Ausführung außerhalb von Tests:

```bash
./scripts/fix-venv-hidden.sh         # schnell, nur .pth-Top-Level
./scripts/fix-venv-hidden.sh --deep  # zusätzlich versteckte Subdirs/.py-Files (teurer rekursiver Sweep)
```

Tritt zusätzlich `ModuleNotFoundError: No module named
'django.contrib.admin.templatetags.admin_urls'` o. ä. auf, fehlen
tatsächlich `.py`-Dateien im venv (Quarantäne hat sie nicht nur
versteckt, sondern entfernt) — Abhilfe ist ein gezielter Reinstall:

```bash
uv sync --reinstall-package django
```

## Wo es weitergeht

- [`.agent/agent.md`](./.agent/agent.md) — Onboarding für Coding-Agents (Vision, Repo-Layout, Konventionen).
- [`docs/workspaces.md`](./docs/workspaces.md) — Cargo-Style Workspaces (Phase 4): Root-Lockfile, Per-Member-Outputs, MVS-Konflikt-UX.
- [`docs/conformance.md`](./docs/conformance.md) — Build-Smoke gegen echte Toolchains (Phase 5a: React/Angular via `tsc --noEmit`, SwiftUI via `swiftc -typecheck`) **+ Cross-Consistency-Sweep**: `5 Specs × 3 Targets × 4 Pfade (Local/CLI/MCP/Web)` byte-identisch via `apps/web/backend/tests/test_cross_consistency_sweep.py`.
- [`docs/visual-regression.md`](./docs/visual-regression.md) — **Phase 5d Voller Sweep**: Visual-Regression über `4 UI-Specs × {react, angular} = 8 Pfade` mit committed Referenz-PNGs (flache Konvention `<spec>-<target>.png`), Recorder-Script `scripts/record_visual_snapshots.py`, ein-Job-CI (`visual-regression.yml`), 10 % Default-Tolerance, Determinismus-Härte mittel (reduce-motion + color-scheme:light + monospace-Font-Stack).
- [`.agent/plans/archive/phase-5d-visual-regression-coverage.md`](./.agent/plans/archive/phase-5d-visual-regression-coverage.md) — Abgeschlossen: Voller Visual-Regression-Sweep über 8 Pfade + Recorder-Script + Determinismus-Härte + Artifact-Upload bei CI-Failure.
- [`.agent/plans/archive/phase-5c-visual-regression-skeleton.md`](./.agent/plans/archive/phase-5c-visual-regression-skeleton.md) — Abgeschlossen: Visual-Regression-Skeleton (`VisualRegressionBackend` + `PlaywrightPixelmatchDriver` + `visual_regression`-Pytest-Marker + `visual-regression.yml`-CI).
- [`.agent/plans/archive/phase-5b-conformance-sweep.md`](./.agent/plans/archive/phase-5b-conformance-sweep.md) — Abgeschlossen: Replay-Cache-Recording für Angular/SwiftUI + echte Spec×Target-Build-Smokes + 75-Pfad-Cross-Consistency-Sweep.
- [`.agent/plans/speccify-plan.md`](./.agent/plans/speccify-plan.md) — Master-Plan (langfristige Vision & Roadmap).
- [`.agent/plans/archive/phase-5a-conformance-backends.md`](./.agent/plans/archive/phase-5a-conformance-backends.md) — Abgeschlossen: Conformance-Build-Smoke gegen React/Angular (`tsc --noEmit`) und SwiftUI (`swiftc -typecheck`) inkl. Conformance-CI-Workflow.
- [`.agent/plans/archive/phase-4-workspaces.md`](./.agent/plans/archive/phase-4-workspaces.md) — Abgeschlossen: Workspaces-Iteration (`lock`/`pull`/`add`/`verify` cross-member + MCP-Bridge).
- [`.agent/plans/archive/phase-3-codegen-targets.md`](./.agent/plans/archive/phase-3-codegen-targets.md) — Abgeschlossen: zweites + drittes Codegen-Target (SwiftUI + Angular).
- [`.agent/plans/archive/phase-2-registry-mvp.md`](./.agent/plans/archive/phase-2-registry-mvp.md) — Abgeschlossen: Registry-MVP (Django).
- [`.agent/plans/phase-1d-browser-playground.md`](.agent/plans/archive/phase-1d-browser-playground.md) — Abgeschlossen (alle Steps): Browser-Playground (`apps/web/`); Archivierung nach User-Tag `v0.4.0-phase-1d`.
- [`.agent/plans/archive/phase-1c-mcp-server.md`](./.agent/plans/archive/phase-1c-mcp-server.md) — Abgeschlossen: MCP-Server `speccify-mcp` (stdio).
- [`.agent/plans/archive/phase-1b-react-codegen.md`](./.agent/plans/archive/phase-1b-react-codegen.md) — Abgeschlossen: React-LLM-Codegen + Replay-Cache + `init`.
- [`.agent/plans/archive/phase-1a-resolver-lockfile.md`](./.agent/plans/archive/phase-1a-resolver-lockfile.md) — Abgeschlossen: Resolver + Lockfile + `add`/`pull`/`verify`.
- [`.agent/plans/archive/phase-0-wrap-up.md`](./.agent/plans/archive/phase-0-wrap-up.md) — Phase-0-Wrap-up (abgeschlossen, ADR-Light für Q1–Q5).
- [`.agent/plans/archive/phase-0-spec-schema-spike.md`](./.agent/plans/archive/phase-0-spec-schema-spike.md) — Phase-0-Implementierungs-Plan (abgeschlossen, archiviert).
- [`.agent/plans/archive/phase-1a0-rename-to-speccify.md`](./.agent/plans/archive/phase-1a0-rename-to-speccify.md) — Rebrand `flowcation` → `speccify` (abgeschlossen).

## Status

**OSS-Pivot (2026-07-23)**: Speccify ist jetzt vollständig Open Source — kein
Pro-Plan/Marketplace, kein zentrales Registry. Das Django-Registry (Phase 2)
wurde zurückgebaut (Archiv-Branch `archive/pre-oss-pivot-registry`); Specs
werden künftig über Git-Repos geteilt. Roadmap und Phasen:
[`.agent/plans/pivot-open-source-git-composer.md`](./.agent/plans/pivot-open-source-git-composer.md).
Nächster Schritt: **P2 — API-Vertrag, Komposition & Mock-Generator** als
Fundament für den visuellen Composer (P3).

Davor abgeschlossen: Phasen 0–6 des ursprünglichen Plans (Schema v0, Resolver +
Lockfile, React/SwiftUI/Angular-Codegen, MCP-Server, Browser-Playground,
Workspaces, Conformance + Visual Regression, Landingpage + Doku-Site) —
Details in den archivierten Phasen-Plänen unter `.agent/plans/archive/`.

## Lizenz

MIT — siehe [`LICENSE`](./LICENSE).
