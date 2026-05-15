---
sessionId: session-260513-141400-1c
isActive: true
---

# Requirements

### Overview & Goals

Phase 1a (Resolver + Lockfile + Stub-Codegen + `add`/`lock`/`pull`/`verify`) und Phase 1b (React-LLM-Codegen + `speccify init` + Replay-Cache + `pull`/`verify --offline` + CI-E2E, Tag-Vorschlag `v0.2.0-phase-1b`) sind abgeschlossen. `speccify_core` exponiert stabile APIs: `load_manifest`/`load_lockfile`, MVS-Resolver, `render_for_target(spec, target, generator_pin)`-Dispatcher mit Stub- und React-LLM-Adapter samt Replay-Cache.

**Ziel von Phase 1c:** Einen **MCP-Server** (`speccify-mcp`), der `speccify_core` ans Model-Context-Protocol bindet, damit Coding-Agents (Junie, Claude Code, Cursor, Aider) denselben Workflow wie die CLI haben — ohne Spec-/Lockfile-Wissen im Agenten selbst. Der Server ist ein dünner Adapter; sämtliche Resolver-/Codegen-Logik bleibt in `core/`. Damit wird das Versprechen aus dem Master-Plan ("CLI und MCP gleichberechtigt, eine Implementierung, zwei Schnittstellen", siehe [`speccify-plan.md`](./speccify-plan.md) Z. 89, 91–94, 308, 397) eingelöst.

Single Source of Truth für Phase-1c-Änderungen ist dieses Dokument.

### Scope

**In Scope**
- MCP-Server-Paket `speccify-mcp` (bereits als leeres uv-Workspace-Package vorhanden), das per `stdio`-Transport einen MCP-Server startet (`speccify-mcp` Binary).
- **Tools** (MCP `tools/call`):
  - `resolve(manifest_path)` → Lockfile-Plan (ohne ihn zu schreiben), d. h. resolvierte `spec://`-IDs + Versionen + SHA-256.
  - `lock(manifest_path)` → schreibt `speccify.lock` (entspricht `speccify lock`).
  - `render(spec_id, target, offline?, cache_dir?)` → generierter Code (TSX-Bytes für `target: react`, Markdown-Bytes für `target: stub`) plus `generator_pin`. Schreibt nichts auf Disk.
  - `pull(manifest_path, out_dir, offline?, cache_dir?)` → schreibt generierte Dateien (entspricht `speccify pull`).
  - `verify(manifest_path, out_dir, offline?, cache_dir?)` → Drift-Check (entspricht `speccify verify`).
  - `lint(spec_path)` → Schema-Lint einer einzelnen Spec (entspricht `speccify lint`).
- **Resources** (MCP `resources/list` + `resources/read`):
  - `spec://<scope>/<name>@<version>` — liefert YAML-Bytes (über aktuelle Registry-Resolution).
  - `speccify://manifest` / `speccify://lockfile` — liefert Inhalt des aktuellen Projekts (Projektpfad pro Server-Session als Startup-Argument `--project <path>` oder Env `SPECCIFY_PROJECT_ROOT`).
- **Prompts** (MCP `prompts/list`): mindestens ein Prompt `add-spec` (Vorlage für Agenten: "Füge `@scope/name@semver` zum Projekt hinzu, locke und pulle nach `<out>`"). Klein gehalten — wir lernen die Form in Phase 1d.
- **Transport**: nur `stdio` (Standard für MCP-Clients). Kein HTTP/SSE in 1c.
- **Logging**: strukturierte Logs nach `stderr` (MCP-konform); Log-Level via `--log-level` / `SPECCIFY_LOG_LEVEL`.
- **Tests**:
  - Unit-Tests pro Tool-Handler (Mock-Server-Context, direkt gegen `speccify_core`).
  - Integrationstests, die den Server via `stdio` als Subprocess starten und einen minimalen MCP-Handshake + `tools/list` + ausgewählte `tools/call`-Roundtrips fahren (gegen `example-project/` und `tests/fixtures/llm-cache/`, offline).
- **CI-Erweiterung**: zusätzlicher Step `speccify-mcp smoke (stdio)`, der den Server startet, `tools/list` + `tools/call render @org/button` ausführt und auf erwartete Bytes prüft (offline).
- **Doku**: Abschnitt im `README.md` und in `mcp/README.md` zur Verwendung mit Junie/Claude Code (Config-Snippet).
- **Master-Plan-Sync** + Tag-Vorschlag `v0.3.0-phase-1c` an User.

**Out of Scope**
- `search` über eine Remote-Registry (kommt mit Phase 2 / Registry-Backend). Lokales Pseudo-Registry hat noch keinen Index.
- `publish`/`yank` (Phase 2).
- HTTP/SSE-Transport, Auth, Multi-Project-Sessions.
- Streaming-`render`-Antworten (LLM-Output wird vom Replay-Cache geliefert → synchron ausreichend).
- Eigene LLM-Calls im MCP-Server jenseits dessen, was `speccify_core` ohnehin tut.
- Eigene Schema-Versionierung; MCP-Server folgt der Schema-/Lockfile-Version aus `speccify_core`.

### User Stories
- *Als Coding-Agent (z. B. Junie)* möchte ich über MCP `tools/call lock` und `tools/call pull` aufrufen, damit der Agent keinen Shell-Aufruf der CLI bauen muss und Fehler strukturiert zurückbekommt.
- *Als Entwickler*innen* möchte ich eine MCP-Config (Junie/Claude Code) committen, sodass Teammitglieder Specs aus der Registry direkt über den Agenten ziehen können.
- *Als Phase-1d-Implementierer (Browser-Playground)* möchte ich denselben `render`-Vertrag verwenden, damit Web-UI und Agent-UI auf derselben Logik laufen.

### Functional Requirements
- Server-Binary `speccify-mcp` startet mit `speccify-mcp --project <path>` (Default: CWD); öffnet `stdio`-MCP-Verbindung.
- `tools/list` liefert mindestens die oben gelisteten Tools mit JSON-Schema für Inputs und strukturierten Outputs (`type: "object"`, klare Felder, keine Free-form-Strings als Hauptkanal).
- `tools/call` führt nichts aus, was nicht auch die CLI tun würde — gleiche Defaults (`--offline` falls Lockfile `kind: llm` enthält und kein `ANTHROPIC_API_KEY`/Bedrock-Creds in Env). Fehler werden als MCP-`isError: true` mit menschenlesbarem `content` + `code`-Feld geliefert.
- `resources/read` für `spec://...`: nutzt dieselbe Registry-Resolution wie `speccify add`; offline gegen `registry-fixtures/` in Tests.
- Keine Netzaufrufe im Default-Pfad, wenn `--offline` aktiv oder Cache vollständig.
- Server ist **stateless** zwischen Calls (alle Tools nehmen `manifest_path`/`project_root` als Input bzw. nutzen Startup-Project).

### Non-Functional Requirements
- **Determinismus**: gleiche Inputs → byte-identische Outputs (folgt aus `speccify_core`-Garantien).
- **Latenz**: `tools/list` < 50 ms, `tools/call render` (Cache-Hit) < 200 ms pro Spec.
- **Offline-CI**: alle Tests und der MCP-Smoke-Step laufen ohne Netz gegen `tests/fixtures/llm-cache/` + `registry-fixtures/`.
- **Stabilität des Tool-Vertrags**: Tool-Namen und Input-Schemas sind Teil des öffentlichen Vertrags ab Phase 1c — Änderungen brauchen ein `schema_version`-Bump-Argument im Plan-Dokument vor der Implementierung.


# Technical Design

### Current Implementation (nach Phase 1b)
- `mcp/` ist als uv-Workspace-Package angelegt (`speccify-mcp`), aber leer (`__init__.py` only). `pyproject.toml` deklariert nur `speccify-core` als Dependency.
- `speccify_core` bietet bereits:
  - `load_manifest`, `load_lockfile`, `write_lockfile`, `build_lockfile`.
  - `resolve_dependencies` (MVS, gegen Registry-Pfad).
  - `render_for_target(spec, target, generator_pin, *, offline, cache_dir)` → `list[GeneratedFile]`.
  - `verify`-Logik (Spec-Hashes, Output-Hashes, Generator-Pin-Drift).
- `cli/` ist heute schon ein dünner Adapter — wird zur Vorlage für `mcp/`.

### Key Decisions
1. **Offizielles MCP-Python-SDK (`mcp[cli]`) verwenden** statt Eigen-Implementierung des Protokolls. Begründung: Protokoll-Korrektheit, Maintenance, kompatibel mit Junie/Claude Code out-of-the-box. Risiko: SDK noch jung — wir pinnen exakt eine Version in `mcp/pyproject.toml` und decken Kern-Roundtrip mit eigenen Integrationstests ab.
2. **`stdio` als einziger Transport in 1c.** HTTP/SSE würde Auth/Deploy-Themen aufmachen, die in 1c nicht zielführend sind. Phase 2 (Registry) kann später einen Remote-Transport anbieten.
3. **Project-Root als Startup-Argument**, nicht pro Call. Vereinfacht Tool-Schemas; passt zur Realität (ein Agent arbeitet pro Session in einem Projekt). Tools, die explizit ein anderes Manifest brauchen, akzeptieren `manifest_path` zusätzlich.
4. **Tools spiegeln CLI-Befehle 1:1**, *nicht* feiner. Das hält den Vertrag klein und macht Cross-Test einfach (CLI- und MCP-Outputs müssen für identische Inputs identisch sein).
5. **Kein eigenes Caching im MCP-Server.** Alle Caching-Themen leben in `speccify_core` (Replay-Cache). MCP ist stateless.
6. **Resources statt Tools für Lese-Zugriffe.** `spec://`-URIs als Resources sind die MCP-idiomatische Form; Tools sind für Aktionen mit Seiteneffekten oder Berechnungen.

### Proposed Changes

#### 1. `mcp/pyproject.toml`
- `dependencies = ["speccify-core", "mcp[cli]>=<pinned>"]`.
- `[project.scripts] speccify-mcp = "speccify_mcp.cli:main"`.
- Dev-Dependencies via Workspace-Inheritance (pytest etc.).

#### 2. `mcp/src/speccify_mcp/`
```
mcp/src/speccify_mcp/
├── __init__.py
├── cli.py                # Argparse: --project, --log-level → startet Server
├── server.py             # MCP-Server-Konstruktion, Tool/Resource-Registry
├── tools/
│   ├── __init__.py
│   ├── resolve.py
│   ├── lock.py
│   ├── render.py
│   ├── pull.py
│   ├── verify.py
│   └── lint.py
├── resources.py          # spec://, speccify://manifest, speccify://lockfile
└── prompts.py            # add-spec prompt
```
Jede Tool-Datei: schmaler Adapter, der Input-Modell (pydantic) validiert, in `speccify_core` aufruft, Ergebnis als strukturierten MCP-`ToolResult` (mit `structuredContent`) zurückgibt.

#### 3. Tests
- `mcp/tests/test_tools_unit.py`: pro Tool ein Happy-Path + ein Fehler-Path (z. B. fehlendes Lockfile).
- `mcp/tests/test_server_integration.py`: spawnt `speccify-mcp --project <tmp example-project copy>` als Subprocess, fährt MCP-Handshake mit dem offiziellen Client aus dem SDK, ruft `tools/list`, `resources/list`, `tools/call render @org/button` (offline) und vergleicht Bytes mit `tests/fixtures/llm-cache`-Erwartung.
- `mcp/tests/test_cross_consistency.py`: ruft denselben Roundtrip einmal über CLI (`subprocess`) und einmal über MCP (`tools/call`), vergleicht `out/`-Bytes — sicherheitsnetz gegen Drift zwischen CLI- und MCP-Pfad.

#### 4. CI (`.github/workflows/ci.yml`)
- Neuer Step `speccify-mcp smoke (stdio, offline)`: startet Server gegen ein `mktemp -d`-Projekt mit `init`+`add`+`lock` Vorlauf, ruft `tools/call render @org/button` und `tools/call verify`, checkt Exit-Code + erwartete Output-Datei.

#### 5. Doku
- `README.md`: neuer Abschnitt "MCP-Server" mit Junie-/Claude-Code-Config-Snippet (`mcpServers: { speccify: { command: "speccify-mcp", args: ["--project", "."] } }`).
- `mcp/README.md`: ausführlichere Doku (Tools, Resources, Beispiel-Calls, offline-Default).

#### 6. Plan- & Status-Sync
- `AGENTS.md` "Aktuelle Phase" auf 1c (aktiv) umstellen.
- `.agent/status.md` + `.agent/log.md` synchron pro Step.

### Risks & Mitigations
- **SDK-API-Drift**: `mcp[cli]` ist noch jung; ein Minor-Bump kann Tool-Signaturen ändern. → Exakter Version-Pin + Integrationstests.
- **Cross-Plattform `stdio`**: Windows/macOS-Pipe-Verhalten unterschiedlich. → Tests laufen auf macOS-Runner in CI (wie bisher); Windows wird erst in Phase 2 angefasst.
- **Tool-Vertrag zementiert sich früh**: → Bewusst klein halten, in 1c nur die 6 Tools, alles weitere in einen Phase-1c-Follow-up-Plan.


# Implementation Plan

### Step 0 — Setup & Pin
- [x] `mcp[cli]`-Version recherchieren und exakt pinnen (in `mcp/pyproject.toml`). → PyPI-Latest `mcp 1.27.1` (Extra `cli`, `requires_python>=3.10`); gepinnt auf `mcp[cli]>=1.27.1,<2.0` (SemVer-Major-Korridor; harte Untergrenze auf der heute auf PyPI verfügbaren Version).
- [x] `uv sync --all-packages` grün, `uv run pytest` weiter 134 grün. → 23 neue Pakete installiert (`mcp==1.27.1` + Transitive: `anyio`, `httpx`, `httpx-sse`, `pydantic` 2.13, `pydantic-settings`, `python-multipart`, `sse-starlette`, `starlette`, `uvicorn`, …), `uv.lock` aktualisiert; 134 Tests grün; ruff + format clean. **Side-Quest** (vgl. Log): `.venv` musste mit `--reinstall` neu gebaut werden wegen präexistierender `_editable_impl_*.pth`-Artefakte ohne Trailing-Newline — kein Repo-Change nötig.

### Step 1 — Server-Skeleton + `tools/list`
- [ ] `speccify_mcp.cli:main` mit `--project`/`--log-level`.
- [ ] `server.py` registriert leeres Tool-Set + Health-Check.
- [ ] Unit-Test: Server lässt sich instanziieren; `tools/list` antwortet leer.

### Step 2 — Tools (read-only): `resolve`, `lint`, `render`
- [ ] Adapter + Tests pro Tool (Happy + Fehlerpfad).
- [ ] Integrationstest gegen `example-project/` (offline, gegen `tests/fixtures/llm-cache`).

### Step 3 — Tools (write): `lock`, `pull`, `verify`
- [ ] Adapter + Tests; `pull`/`verify` mit `--offline`-Default, wenn keine Live-Creds.
- [ ] Cross-Consistency-Test CLI ↔ MCP.

### Step 4 — Resources + Prompts
- [ ] `spec://` Resource-Provider gegen Registry-Resolution.
- [ ] `speccify://manifest|lockfile`.
- [ ] `add-spec` Prompt.

### Step 5 — CI + Doku
- [ ] CI-Step `speccify-mcp smoke (stdio, offline)`.
- [ ] `README.md` + `mcp/README.md` aktualisieren.

### Step 6 — Wrap-up
- [ ] `speccify-plan.md` Phase 1c als abgeschlossen markieren + MCP-Tool-Vertrag inline dokumentieren.
- [ ] `AGENTS.md` auf 1d umstellen.
- [ ] `.agent/status.md`/`.agent/log.md` Sync.
- [ ] Tag-Vorschlag `v0.3.0-phase-1c` an User (nicht selbst setzen).

### Open Questions (vor Step 1 zu klären)
1. **Welche MCP-SDK-Version pinnen?** — `mcp[cli]` Latest auf PyPI prüfen; ggf. `>=x.y,<x.(y+1)`.
2. **`spec://`-Resources: nur lokale Registry-Pfade oder auch remote (HTTPS)?** — Vorschlag: nur lokal in 1c, remote ab Phase 2.
3. **Cross-Consistency-Test: per `subprocess` CLI + MCP, oder reicht ein Snapshot des `out/`-Inhalts?** — Snapshot-basiert ist günstiger, deckt aber Drift nicht direkt ab. Empfehlung: beides als ein einziger Test.
