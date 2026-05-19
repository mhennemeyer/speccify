---
sessionId: session-260519-105200-1d
isActive: true
---

# Requirements

### Overview & Goals

Phasen 1a/1b/1c sind abgeschlossen: `speccify-core` exponiert einen stabilen Render-Vertrag (`render_for_target(spec, target, generator_pin)` mit Replay-Cache), `speccify-cli` und `speccify-mcp` sind dünne, byte-identische Adapter darüber. Damit ist die Codegen-Pipeline so weit gefestigt, dass eine zweite Nutzungs-Oberfläche jenseits von Terminal/Agent möglich ist.

**Ziel von Phase 1d:** Ein **Browser-Playground** unter `apps/web/`, der dieselbe Codegen-Pipeline anfasst wie CLI und MCP und das Versprechen aus dem Master-Plan einlöst, dass die Website *die* Demo- und Onboarding-Oberfläche von Speccify ist (siehe [`speccify-plan.md`](./speccify-plan.md) Z. 6, 97–103, 280, 302–308 sowie Phase-1d-Zeile „Browser-Playground auf der Website, der dieselbe Codegen-Pipeline nutzt").

Konkret soll ein User im Browser:
1. Eine der eingecheckten Referenz-Specs (`specs/*.yaml`) oder eine selbst eingegebene YAML-Spec sehen,
2. Auf „Render → React (TSX)" klicken und
3. das generierte TSX **deterministisch und ohne Netzaufruf** angezeigt bekommen (Replay-Cache-Hit, byte-identisch zur CLI).

Das Live-LLM (Bedrock) ist in 1d **bewusst nicht** verdrahtet — der Playground demonstriert die Pipeline, nicht das Modell. Cache-Misses zeigen eine klare Fehlermeldung samt Maintainer-Hinweis, wie ein neuer Cache-Eintrag via `scripts/record_llm_cache.py` erzeugt wird.

Single Source of Truth für Phase-1d-Änderungen ist dieses Dokument.

### Scope

**In Scope**
- Neues uv-fremdes Sub-Projekt `apps/web/` (Node/TypeScript-Stack) als **Next.js 15** (App-Router) + React 19 + TypeScript. Build via `pnpm`/`npm` (Empfehlung: `pnpm`, weil es out-of-the-box ohne globale Konfiguration funktioniert; finale Wahl in Step 1).
- **Backend-Adapter in Python** (`apps/web/backend/` oder neues Workspace-Paket `speccify-web-backend`), das die `speccify-core`-Render-Pipeline über eine schmale HTTP-Schicht (FastAPI) freigibt — oder, falls einfacher und ausreichend: ein Node-Child-Process, der `speccify-cli render` (neu) bzw. einen kleinen Python-CLI-Render-Helfer aufruft. **Designentscheidung in Step 1**, beide Varianten im Plan dokumentiert.
- **MVP-Endpoints**:
  - `GET /api/specs` → Liste der eingecheckten Referenz-Specs (`specs/*.yaml`), mit Spec-ID + Title + raw YAML.
  - `POST /api/render` (Body: `{spec_yaml: string, target: "react"}`) → `{files: [{path, content}], generator_pin}`. **Offline-only:** ruft `speccify_core.render_for_target` mit `ReplayCacheClient` gegen `tests/fixtures/llm-cache/`; Cache-Miss → strukturierter 422-Fehler mit Hinweistext.
- **Frontend-MVP**:
  - Linke Spalte: Spec-Picker (Dropdown der Referenz-Specs) + Monaco-/CodeMirror-Editor mit der YAML der gewählten Spec (editierbar, aber Edit ⇒ erwartbar Cache-Miss).
  - Rechte Spalte: „Render React" Button → zeigt generiertes TSX (read-only Editor mit Syntax-Highlighting) + `generator_pin`-Block (Model, Prompt-Version, Seed, Cache-Key) + Copy-Button.
  - Fehlerzustand: Cache-Miss prominent erklärt („Diese Spec ist noch nicht im Replay-Cache. Maintainer: `uv run python scripts/record_llm_cache.py …`").
- **Deployment-Geschichte (nur dokumentiert, kein Live-Deploy in 1d)**: Vercel/Cloudflare Pages für Frontend, Python-Backend als separate Service-Komponente (z. B. Fly.io / Render). Wahl & Setup sind explizit *Phase 2*, weil sie eng an Registry + Auth hängen.
- **Tests**:
  - Backend: Pytest-Tests gegen `render`-Endpoint (happy path mit Cache-Hit, Cache-Miss → 422, unbekanntes Target → 400).
  - Frontend: Mindestens ein Playwright-/Vitest-Smoke-Test, der die Pipeline „Spec auswählen → Render klicken → TSX wird angezeigt" gegen das laufende Backend einmal abgeht (CI-optional in 1d, mind. lokal lauffähig).
- **CI**: ein zusätzlicher Workflow-Job `apps/web build + smoke` (offline, gegen Repo-Cache).
- **Doku**: `apps/web/README.md` (Quickstart, Stack, Limitierungen, „nur Replay-Cache"), Top-Level-`README.md`-Abschnitt „Browser-Playground (Phase 1d)".
- **Master-Plan-Sync** + Tag-Vorschlag `v0.4.0-phase-1d` an User.

**Out of Scope**
- Live-LLM-Aufrufe (Bedrock/Anthropic) aus dem Browser oder Backend. *Begründung*: Credentials gehören nicht in den Browser, ein produktionsreifer Backend-Proxy mit Rate-Limit/Auth ist Phase 2.
- Persistenz / User-Accounts / OAuth / öffentliche URLs zum Teilen einer Render-Session.
- Multi-Target-Rendering (nur `react` in 1d; `stub` evtl. als Dev-Affordanz, aber nicht UI-prominent).
- Visuelle Live-Preview (Rendered Component im iFrame). Erwähnt im Master-Plan als Phase 5 (Live-Preview / Multi-Target-Renderer im Editor) — bewusst nicht 1d.
- Discovery/Suche/Trending — Phase 2 (Registry).
- Refinement-Diskussionen / Kommentare / Forks — Phase 5.
- Tauri/Desktop-Bezüge.

### User Stories
- *Als Erstbesucher der Website* möchte ich auf einer Demo-Seite eine vorhandene Spec auswählen und mit einem Klick deren React-Code generieren sehen, damit ich Speccify in unter 60 Sekunden verstehe.
- *Als Entwickler*innen* möchte ich die eingecheckten Referenz-Specs direkt im Browser inspizieren und mit dem CLI-Output vergleichen können, damit ich CLI-/MCP-/Web-Pipeline als „dieselbe Pipeline" wahrnehme.
- *Als Maintainer* möchte ich beim Cache-Miss eine klare Anleitung sehen, wie ich den Cache-Eintrag offline nachziehe.

### Functional Requirements
- Playground rendert byte-identisch zu `speccify pull` / MCP `tools/call pull` für dieselbe Spec + denselben Target (gleicher Replay-Cache, gleicher `render_for_target`-Pfad).
- Editierbarer Spec-Editor: bei Spec-Änderung wird die Cache-Key-Berechnung mitlaufen; geänderte Spec ⇒ Cache-Miss-Pfad (UI dokumentiert das explizit).
- Render-Antwort enthält den `generator_pin` (Model, Prompt-Version, Seed, Cache-Key) und macht damit Reproduzierbarkeit sichtbar.
- Backend lehnt unbekannte Targets, ungültiges YAML und Schema-Verstöße strukturiert ab (`{error_code, message, details}`) — gleiche Fehler-Codes wie CLI/MCP, soweit existierend.
- Keine Netzaufrufe im Default-Pfad (offline-CI).

### Non-Functional Requirements
- **Determinismus**: Browser-Output für eingecheckte Specs ist byte-identisch zum CLI-/MCP-Output (Cross-Consistency-Test gegen alle drei Pfade).
- **Latenz**: `/api/render` (Cache-Hit) < 300 ms; initiales Seitenladen < 1.5 s lokal.
- **Stack-Konsistenz**: Frontend nutzt React 19 + Next.js App-Router; Code-Style folgt EditorConfig (2-space, LF, final newline). Keine Klassen-Components, keine Default-Exports außer wo Next.js sie erzwingt.
- **Offline-CI**: Build + Tests + Smoke laufen ohne Netz (Cache + Referenz-Specs aus dem Repo).
- **Tool-Vertrag stabil**: `/api/render` ist ab 1d versioniert (`/api/v1/render`) — Breaking Changes brauchen Bump-Begründung im Phase-Plan.


# Technical Design

### Current Implementation (nach Phase 1c)
- `speccify_core` bietet bereits den vollständigen Render-Vertrag inkl. Replay-Cache (`ReplayCacheClient`, Default `tests/fixtures/llm-cache/`).
- `speccify_cli` (Sub-Command `pull`, `verify`, `render`-äquivalent) und `speccify_mcp` (Tool `render`) sind byte-identische Adapter — Cross-Consistency-Test in `mcp/tests/test_tools_write.py` bestätigt es.
- `apps/` existiert noch nicht als Verzeichnis im Repo-Layout, ist aber im Master-Plan reserviert (`apps/web/`).
- Es gibt **kein** JavaScript-/Node-Tooling im Repo. EditorConfig erwartet 2-space für „Rest"-Dateien (passt zu TS/JS-Konventionen).

### Key Decisions
1. **Next.js 15 (App-Router) als Default-Stack**, vom User in der Phase-Planung explizit so gewählt (gegen SvelteKit). Begründet zusätzlich durch 1:1-Match zum React-LLM-Output (TSX) — der Playground kann die generierten Komponenten später auch direkt rendern (Phase 5), ohne den Stack zu wechseln.
2. **MVP nutzt ausschließlich den eingecheckten Replay-Cache**, kein Live-Bedrock. Vom User explizit so entschieden. Cache-Miss ist erwartetes Verhalten bei editierten Specs und wird als UX-Pfad ausgestaltet, nicht als Bug.
3. **Backend in Python (FastAPI) bevorzugt** statt Node, weil dadurch `speccify-core` direkt in-process aufgerufen wird (kein Marshalling über Subprocess + JSON). Alternative (Node-Subprocess-Aufruf des CLI) wird in Step 1 abgewogen. Empfehlung: FastAPI als kleines Sub-Paket im `uv`-Workspace; im Dev liefert Next.js statisch + ruft `localhost:8000` an, im Build wird das Backend separat gestartet.
4. **Versioniertes Backend-API** (`/api/v1/...`) ab Tag 1 — Browser ist Außenwelt, Vertrag wird zementiert.
5. **Keine Server-Components für Render-Output.** Der Render-Call läuft client-getriggert (Button → `fetch`) gegen das FastAPI-Backend; das hält die Architektur einfach und das Backend lebt unabhängig vom Frontend-Framework.
6. **Monaco** als Code-Editor (read + write, YAML + TSX), weil im Browser-Playground-Kontext Standard, gut typisiert und framework-agnostisch. Alternative CodeMirror 6 ist legitim — Entscheidung in Step 2.

### Proposed Changes

#### 1. Workspace-Erweiterung
- Top-Level `pyproject.toml` um `apps/web/backend` als uv-Workspace-Member erweitern.
- Neues Python-Paket `apps/web/backend/` (`speccify-web-backend`): `pyproject.toml` mit `fastapi`, `uvicorn[standard]` (Dev) + `speccify-core`.
- Frontend-Projekt `apps/web/frontend/` als reines Next.js-Projekt (`package.json` mit `next@15`, `react@19`, `typescript`, `@monaco-editor/react`).
- `apps/web/README.md` als Stack-/Quickstart-Doku.

#### 2. Backend-Skeleton (`apps/web/backend/src/speccify_web_backend/`)
```
apps/web/backend/src/speccify_web_backend/
├── __init__.py
├── app.py              # FastAPI-App-Fabrik, CORS für http://localhost:3000
├── routes/
│   ├── __init__.py
│   ├── specs.py        # GET /api/v1/specs
│   └── render.py       # POST /api/v1/render
├── services/
│   └── render.py       # dünner Wrapper um speccify_core.render_for_target
└── settings.py         # SPECCIFY_PROJECT_ROOT, SPECCIFY_CACHE_DIR, offline-Default
```
- Service-Layer ruft `render_for_target(spec, target, llm_client=ReplayCacheClient(...))` mit `offline=True`.
- Fehler-Mapping: `CacheMissError` → 422 `{error_code: "cache_miss", message, hint}`; YAML/Schema-Fehler → 400 `{error_code: "spec_invalid", message, details}`; unbekanntes Target → 400 `{error_code: "unknown_target"}`.

#### 3. Frontend-Skeleton (`apps/web/frontend/`)
```
apps/web/frontend/
├── package.json
├── tsconfig.json
├── next.config.ts
├── app/
│   ├── layout.tsx
│   ├── page.tsx           # Landing/Hero + Link zum Playground
│   └── playground/page.tsx
├── components/
│   ├── SpecPicker.tsx
│   ├── SpecEditor.tsx     # Monaco YAML
│   ├── RenderOutput.tsx   # Monaco TSX (read-only) + generator_pin
│   └── ErrorPanel.tsx
└── lib/
    └── api.ts             # fetch-Wrapper für /api/v1/{specs,render}
```
- Pure Function Components (FP-Style, hooks-driven; vgl. `.agent/functional.md`).
- Kein globales State-Management (Zustand local, props down). React-Query *kann* eingeführt werden, ist aber für 2 Endpoints overkill.

#### 4. Tests
- `apps/web/backend/tests/test_render_route.py` (Pytest, FastAPI TestClient):
  - happy path: `@org/button` (aus `specs/`) → 200 + TSX-Bytes + `generator_pin.kind=llm`.
  - edited spec (Title-Change) → 422 `cache_miss`.
  - unknown target → 400.
  - invalid YAML → 400.
- **Cross-Consistency-Test** (in Pytest, `apps/web/backend/tests/test_cross_consistency.py`): ruft denselben Roundtrip einmal über `speccify_cli.commands.pull.run_pull`, einmal über `speccify_mcp.tools.run_pull`, einmal über das Backend-Service-Modul (`speccify_web_backend.services.render`) und vergleicht TSX-Bytes byte-identisch. Schließt den Dreieck-Vertrag CLI ↔ MCP ↔ Web.
- Frontend: ein `vitest`- oder `playwright`-Smoke (Wahl in Step 3); CI-Pflicht nur, wenn Setup leichtgewichtig.

#### 5. CI (`.github/workflows/ci.yml`)
- Neuer Job `apps/web backend (offline)`: `uv run pytest apps/web/backend/tests`.
- Neuer Job `apps/web frontend build`: `pnpm --filter apps/web/frontend build` (oder `npm`), offline (alle Deps via Lockfile).
- Optional: Playwright-Smoke in einem separaten Job mit `pnpm exec playwright install --with-deps chromium` (nur wenn Step 3 das einbaut).

#### 6. Doku
- `apps/web/README.md`: Quickstart (Backend + Frontend separat starten), Stack-Begründung, Replay-Cache-Limitierung, Verweis auf Plan.
- Top-Level-`README.md`: Abschnitt „Browser-Playground (`apps/web/`)" mit Screenshots-TODO und Verweis auf `apps/web/README.md`.

#### 7. Plan- & Status-Sync
- `AGENTS.md` „Aktuelle Phase" auf 1d (aktiv) umstellen, sobald Step 1 startet.
- `speccify-plan.md` Phase 1d ausbauen (Tool-Vertrag `/api/v1/...`, Decision-Block) — in Step 6.
- `.agent/status.md` + `.agent/log.md` synchron pro Step.

### Risks & Mitigations
- **Stack-Drift JS/Python**: zwei Toolchains erhöhen Komplexität. → Strenges Repo-Layout (`apps/web/{backend,frontend}`), klare CI-Trennung, ein einziger gemeinsamer Smoke-Test.
- **Cache-Miss-UX wirkt wie Bug**: → Klare Fehlertexte, Maintainer-Hinweis, evtl. Toggle „Spec wurde editiert ⇒ Cache-Miss erwartet" prominent.
- **Frontend-Lockfile**: `pnpm-lock.yaml`/`package-lock.json` einchecken; offline-CI verlangt `--frozen-lockfile`.
- **CORS / Dev-Proxy**: simple Lösung in 1d → FastAPI mit `CORSMiddleware(allow_origins=["http://localhost:3000"])`. Prod-Proxy ist Phase 2.
- **Bedrock-Verlockung**: spätere Erweiterung um Live-LLM nicht im 1d-Scope einbauen; expliziter Out-of-Scope-Vermerk hier dokumentiert.


# Implementation Plan

### Step 0 — Setup & Stack-Entscheidungen
- [ ] Paket-Manager-Wahl (`pnpm` vs. `npm`) finalisieren; Node-Version pinnen (`.nvmrc` + `package.json` `engines`).
- [ ] FastAPI-Variante final bestätigen (vs. Node-Subprocess); `apps/web/backend/pyproject.toml` mit gepinnten Versionen (`fastapi`, `uvicorn`) erstellen, als uv-Workspace-Member registrieren.
- [ ] `uv sync --all-packages` grün; bestehende 174 Tests bleiben grün.

### Step 1 — Backend-MVP
- [ ] `apps/web/backend/src/speccify_web_backend/` mit `app.py`, `routes/specs.py`, `routes/render.py`, `services/render.py`, `settings.py`.
- [ ] `/api/v1/specs` liefert Liste der `specs/*.yaml` aus `SPECCIFY_PROJECT_ROOT` (Default: Repo-Root) mit `{id, title, version, yaml}`.
- [ ] `/api/v1/render` ruft `speccify_core.render_for_target` mit `ReplayCacheClient(cache_dir=tests/fixtures/llm-cache)`, offline-only.
- [ ] Fehler-Mapping (`cache_miss` 422, `spec_invalid` 400, `unknown_target` 400) inkl. Hinweistext.
- [ ] Pytest-Suite (`test_render_route.py`, `test_specs_route.py`, `test_cross_consistency.py`) grün; `uv run pytest` weiter komplett grün.

### Step 2 — Frontend-Skeleton + Spec-Picker
- [ ] Next.js 15 / React 19 / TS-Setup unter `apps/web/frontend/`, ESLint-/Prettier-Config angelehnt an EditorConfig.
- [ ] `app/playground/page.tsx` mit Spec-Picker (Dropdown) + Monaco-YAML-Editor (initial readonly aus `/api/v1/specs`).
- [ ] `lib/api.ts` mit typed `fetch`-Wrappern; Type-Schema via `zod` aus Backend-Response.
- [ ] `pnpm --filter apps/web/frontend build` grün lokal.

### Step 3 — Render-Flow + Output-Panel
- [ ] „Render React" Button → POST `/api/v1/render` mit aktueller Editor-YAML + `target: "react"`.
- [ ] `RenderOutput.tsx` zeigt TSX (Monaco read-only), `generator_pin` als Detail-Disclosure, Copy-Button.
- [ ] `ErrorPanel.tsx` für `cache_miss` (mit Maintainer-Hinweis) + `spec_invalid` (mit `details`).
- [ ] Playwright-Smoke `tests/e2e/playground.spec.ts`: lädt Seite, wählt `button.yaml`, klickt Render, erwartet TSX-Substring (z. B. `export function Button`).

### Step 4 — Cross-Consistency + Doku
- [ ] `test_cross_consistency.py` deckt CLI ↔ MCP ↔ Web byte-identisch ab (mind. 1 Referenz-Spec).
- [ ] `apps/web/README.md` final (Stack, Quickstart `uv run uvicorn ... & pnpm dev`, Limitierungen, Replay-Cache-Hinweis).
- [ ] Top-Level-`README.md`: neuer Abschnitt „Browser-Playground" + Verweise.

### Step 5 — CI
- [ ] Neue CI-Jobs: `apps/web backend (offline)` (Pytest) + `apps/web frontend build` (pnpm build, offline mit `--frozen-lockfile`).
- [ ] Optional Job: `apps/web e2e smoke` (Playwright), nur falls Step 3 stabil verdrahtet ist.

### Step 6 — Wrap-up
- [ ] `speccify-plan.md` Phase 1d als abgeschlossen markieren + Tool-Vertrag `/api/v1/...` inline dokumentieren (Endpoints, Fehler-Codes, Replay-Cache-Limitierung).
- [ ] `AGENTS.md` „Aktuelle Phase" auf „Phase 1d abgeschlossen, nächste Phase 2 (Registry-MVP)" umstellen.
- [ ] `.agent/status.md`/`.agent/log.md` Sync (Step 6 abgehakt, nächster Schritt = Phase-2-Plan-Entwurf nach User-Tag).
- [ ] Tag-Vorschlag `v0.4.0-phase-1d` an User dokumentiert (selbst nicht gesetzt, vgl. `rules.md`).

### Open Questions (vor Step 1 zu klären)
1. **FastAPI in-process vs. Node-Subprocess-Aufruf des CLI?** — Empfehlung: FastAPI in-process (kein Marshalling, schneller, leichter zu testen). Bestätigung in Step 0.
2. **`pnpm` oder `npm`?** — Empfehlung: `pnpm` (Workspace-fähig, schneller, deterministischer Store). Falls Team keine `pnpm`-Erfahrung hat: `npm` ist legitim.
3. **Monaco oder CodeMirror 6?** — Empfehlung: Monaco (in-house Standard, gute YAML-/TSX-Unterstützung). CodeMirror falls Bundle-Size kritisch wird.
4. **Spec-Auswahl im UI: nur eingecheckte Referenz-Specs oder auch beliebige Datei-Uploads?** — Vorschlag: 1d nur eingecheckte Specs (+ Editieren); Uploads ab Phase 2 mit Registry.
5. **Playwright in CI ab 1d oder erst 1d-Follow-up?** — Vorschlag: lokal in 1d, CI-Pflicht erst sobald Setup stabil (Step 5 markiert es als optional).
