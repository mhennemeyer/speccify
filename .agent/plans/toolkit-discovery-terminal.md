---
isActive: true
---

# Plan: Toolkit-Vollausbau — Discovery, MCPs, Toolbox & Agent-Terminal

**Angelegt 2026-07-25 nach BO-Zielvorgabe** („bevor wir Composer/Specs
weiter schärfen, den anderen Teil zu Ende bringen — iKanbanAi wartet").
Status: **Entwurf zum Refinen** (Open Questions unten). Dieser Plan
übernimmt die Ausführung von R1/R2 aus
[`rust-neustart-toolkit-mcps.md`](./rust-neustart-toolkit-mcps.md)
(bleibt Kontrakt-Referenz) und den Feinschliff A2 aus
[`desktop-app-und-composer.md`](./desktop-app-und-composer.md) (A0/A1 ✅).

## Ziele (BO, 2026-07-25)

1. **Discovery-MCP**: einem anfragenden Agent alle MCPs und Tools
   anbieten — inklusive Konfiguration (ready-to-use Client-Config).
2. **Toolbox** erstmal wie in dotagent (Manifeste: tool / mcp / kb).
3. **MCPs**: Parallels, Exec, Playwright.
4. **Eigene Tools und MCPs erstellen**, gespeichert in einem
   **Working Dir** (Auswahl in den Settings).
5. **Rechte Seitenleiste mit Terminal** für einen Agent, gestartet im
   Working Dir; der Agent muss Speccify kennen (`.claude`/`CLAUDE.md`/
   `.mcp.json` im Working Dir — fehlende Einträge per Klick in den
   Settings anlegbar).
6. **Chat-UI-Elemente wie in iKanbanAi** im Terminal-Bereich: Buttons
   (Einzelantwort), Checkbox-Liste (Mehrfachauswahl), Formular
   (Antwort-Liste).
7. Normales bash/zsh-Terminal für macOS/Linux; **Windows zurückgestellt**.

## Referenz-Befunde (gelesen 2026-07-25)

- **dotagent-Toolbox** (`src/dotagent/registry/`): TOML-Manifeste mit
  `kind = tool|mcp|kb`, `name/slug/description/tags/category`,
  optional `[run] command/args/transport(stdio|sse|http)/autostart`,
  `[requires] binaries`; Quellen global + projekt; `registry list
  --json` speist den Library-Tab; `registry scaffold` legt neue an.
- **Parallels-MCP** (`src/dotagent/mcp/parallels.py`): .NET-Workflows in
  der Windows-VM via `prlctl exec` (SYSTEM-Kontext, `\\Mac\Home`-Pfad-
  Mapping, `chcp 65001`), eigenes Allowlist-Paar
  (`parallels-allowlist/pending.json`, Default nur `dotnet …`), Tools
  u. a. vm_list/vm_status/vm_start + Befehl ausführen; Port 8766.
- **iKanbanAi-Chat-Elemente**: Der Agent ruft ein Tool **`ask_bo`** auf;
  die App rendert eine `ChatInteraction` (`kind: buttons |
  multi_select | form`, `prompt`, `options[]`, `fields[{label,
  recommended}]`), der BO klickt, die Antwort (`selectedOptions[]`,
  `fieldValues[]`) geht als Tool-Result zurück. Unbekannte Kinds
  degradieren tolerant zu Hinweistext (Vorwärts-Kompatibilität).
  In iKanbanAi ist `ask_bo` ein In-Process-API-Tool — bei uns läuft der
  Agent als **Claude Code im Terminal**, also kommt `ask_bo` als
  MCP-Tool aus einem von der App gehosteten Server (D4 unten).

## Architektur-Empfehlungen (D — bitte refinen/bestätigen)

- **D1 Toolbox-Format**: dotagent-TOML **1:1 übernehmen** (kein neues
  Format; Schema dokumentiert als `schema/toolbox-manifest.schema.json`
  nur informativ). Drei Quellen mit Vorrang:
  `builtin` (im Repo, kuratiert) → `~/.speccify/toolbox/` (global) →
  `<workingdir>/.speccify/toolbox/`. Slug-Kollision: spezifischste
  Quelle gewinnt.
- **D2 Discovery-MCP** (`crates/discovery-mcp`, Streamable HTTP wie
  Exec, Vorschlag Port **8767**, gleicher JSON-RPC-Layer): Tools
  - `mcp_list` — alle Toolbox-MCPs + Laufzeitstatus (running/port) +
    **`client_config`** pro Eintrag: fertiges `.mcp.json`-Fragment
    (http-URL bzw. command/args für stdio) zum direkten Einhängen.
  - `tools_list` — Toolbox-Einträge `kind=tool` **plus** Aktionen
    (`.agent/actions.json` global + Working Dir, Schema v1 aus R0).
  - `actions_propose` — wie iKanbanAi-Flow (source=agent,
    confirmed=false).
  - `scaffold` — legt Tool-/MCP-Manifest im Working Dir an (Ziel 4
    auch für Agents, nicht nur per UI).
- **D3 MCP-Bestand**: Exec = Rust-Port (Kontrakt-Harness aus R0 ist
  das Gate). Parallels = Rust-Port des dotagent-Servers (Port 8766,
  gleiche Allowlist-Semantik). Playwright = **nicht selbst bauen**:
  Toolbox-Manifest für `npx @playwright/mcp@latest` (stdio), von
  Supervisor/Discovery verwaltet.
- **D4 `ask_bo`-Brücke**: Die Desktop-App hostet einen kleinen
  **desktop-ui-MCP** (im App-Prozess, Rust, localhost): Tool `ask_bo`
  mit iKanbanAi-identischem Schema (buttons/multi_select/form). Der
  Tool-Call **blockiert**, bis der BO in der Seitenleiste klickt;
  Antwort = Tool-Result. Claude Code im Terminal bekommt ihn über die
  `.mcp.json` des Working Dir. Schema-Gleichheit mit iKanbanAi ist
  Vertrag (ein Konzept, zwei Clients).
- **D5 Terminal**: `xterm.js` im Frontend + `portable-pty` Rust-seitig;
  Login-Shell des Users (macOS: zsh), cwd = Working Dir, mehrere Tabs
  später. Kein Windows-Support in dieser Phase. Das Terminal ist ein
  ECHTES Terminal — die Chat-Elemente rendern daneben/darüber in der
  Seitenleiste (kein PTY-Scraping).
- **D6 Settings**: neuer App-Tab; Persistenz `~/.speccify/settings.json`
  (`working_dir`, später mehr). „Agent-Einweisung"-Sektion zeigt pro
  Datei Status + Anlegen-Klick (Ziel 5): `CLAUDE.md`
  (Speccify-Kurzkontext), `.mcp.json` (discovery + exec + desktop-ui +
  playwright), optional `.claude/settings.json`. Templates liegen im
  Repo (`apps/desktop/templates/…`), Anlegen überschreibt nie.
- **D7 Reihenfolge / kritischer Pfad iKanbanAi**: iKanbanAi spricht den
  Exec-MCP schon (Python) — was fehlt, ist **Discovery** (Aktionsliste/
  MCP-Liste). Deshalb: Toolbox + Discovery VOR dem Exec-Rust-Port;
  der Python-Exec bleibt solange auf 8765 stehen.

## Stufen (T)

### T0 — Refinement ✅ (2026-07-25, BO-Antworten Runde 1)
1. Reihenfolge bestätigt; iKanbanAi erwartet **Aktionen UND `mcp_list`**
   über Discovery.
2. Port 8767 ok, **stdio zusätzlich** zu Streamable HTTP.
3. Toolbox-TOML 1:1 inkl. `kind: kb` bestätigt.
4. **Genau ein** Working Dir global in den Settings.
5. Terminal-Agent: **Autostart-Command in den Settings** konfigurierbar
   (Default `claude`); Start beim Öffnen der Sidebar.
6. `ask_bo` mit Timeout/„später beantworten" wie iKanbanAi.
7. Parallels **so schnell wie möglich** — bleibt direkt hinter dem
   Exec-Port (T5), weil beide denselben JSON-RPC-/Allowlist-Unterbau
   teilen; keine weiteren Stufen dazwischen schieben.
8. Einweisungs-Trio bestätigt; **andere Agents später** (Templates
   dürfen Claude-Code-spezifisch sein).

### T1 — Settings + Working Dir ✅ (2026-07-25)
[x] Settings-Tab (6. Tab), Persistenz `~/.speccify/settings.json`
(`working_dir`, `terminal_autostart_command` Default `claude`),
Working-Dir-Picker; Einweisungs-Dateien mit Status + Klick-Anlage
(CLAUDE.md/.mcp.json/.claude/settings.json aus ins Binary eingebetteten
Templates `src-tauri/templates/`, niemals überschreiben; .mcp.json
enthält discovery :8767 + exec :8765 + playwright-npx). Rust-Modul
`settings.rs` mit 4 Commands + 2 Unit-Tests. Verifikation: cargo
test/clippy/fmt grün, tsc+Vite grün (216 kB).

### T2 — Toolbox nativ ✅ (2026-07-25)
[x] `crates/toolbox` (lib, von App + Discovery geteilt): dotagent-
kompatibler TOML-Parser (gleiche Pflichtfeld-/kind-/transport-Regeln),
drei Quellen mit Slug-Vorrang workingdir > global > builtin, Scaffold
(nie überschreiben, Slug-Validierung), 5 Unit-Tests. Builtin-Manifeste:
speccify-exec + parallels-dotnet (übergangsweise via dotagent-CLI, Wechsel
in T4/T5), speccify-discovery (:8767), playwright (npx, stdio),
speccify-mcp (uv, stdio). App: `toolbox_list`/`toolbox_scaffold`-Commands
(Working Dir aus Settings), Library-Tab liest nativ (dotagent-CLI nur
noch für Doctor), „+ Neues Manifest"-Formular. Verifikation: 7 Rust-Tests
grün, clippy --workspace -D warnings clean, tsc+Vite grün (218 kB).

### T3 — Discovery-MCP MVP ✅ Server-seitig (2026-07-25)
[x] `crates/mcp-core` (neu, geteilter Unterbau): JSON-RPC-Dispatch nach
Kontrakt-Semantik (Notification→202, -32700/-32601, text_result-Form),
Streamable-HTTP (tiny_http, threaded, SSE-Hook für T4 vorbereitet) +
stdio-Transport (ndjson).
[x] `crates/discovery-mcp`: `mcp_list` (Toolbox-MCPs + Laufzeitstatus
via Port-Probe + `client_config`-Fragment: http-URL bzw. command/args;
Port aus `--port`-Args oder Slug-Default 8765/8766/8767), `tools_list`
(Toolbox-Tools + Aktionen global `~/.speccify/actions.json` + Projekt/
Working-Dir `.agent/actions.json`), `actions_propose` (source=agent,
confirmed=false, Dedup nach command — iKanbanAi-Semantik), `scaffold`.
Working Dir aus `~/.speccify/settings.json`, `project`-Argument pro
Aufruf, CLI `--port/--stdio/--working-dir`. 7 Unit-Tests + Live-Smoke
(HTTP + stdio) grün.
[ ] **T3-Rest**: Server-Tab der App auf Toolbox/Discovery umstellen
(Start/Stop via Supervisor statt `dotagent mcp …`) — zusammen mit T4-
Umschaltung sinnvoll. **iKanbanAi-Anbindung passiert drüben** (Discovery
läuft und liefert Aktionen + mcp_list; Sync-Semantik dort klären).

### T4 — Rust-Exec-MCP ✅ (2026-07-25)
[x] `crates/exec-mcp` (Port nach `docs/exec-mcp-contract.md`):
`allowlist.rs` (Token-Präfix-Match via shlex, consume/pending, dep-freier
UTC-Zeitstempel), `exec.rs` (run_command mit 20k-Cap + wait-timeout;
stream_command mit os_pipe-fd-Merge stderr→stdout, ungekappt, Timeout-Kill,
Disconnect-Kill), `lib.rs` (ExecMcp: run_command/run_action/list_actions,
bound/multi, exakte Fehlertexte), stdio + /stream-CLI. **`crates/mcp-core`
Stream-Transport auf tiny_http-Chunked-Reader umgestellt** (schließt sauber,
Disconnect propagiert über den Kanal als BrokenPipe). **Gate: Diff-Harness
28/28 Parität gegen laufende dotagent-Referenz grün**; 10 Rust-Tests inkl.
der 3 Lebensdauer-Tests (Cap/Timeout/Disconnect). builtin `speccify-exec.toml`
zeigt jetzt auf `speccify-exec-mcp --port 8765` (statt dotagent-CLI).
[ ] **Umschaltung Port 8765 in Betrieb + Server-Tab** (Start/Stop via
Supervisor) zusammen mit T5-Wrap; nie beide Server gleichzeitig auf 8765.

### T5 — Parallels-Port + Playwright-Manifest (1 Tag)
Parallels nach Rust (Port 8766, Allowlist-Semantik identisch);
Playwright als verwaltetes Manifest (D3) inkl. Discovery-Eintrag.

### T6 — Terminal-Seitenleiste (1–2 Tage)
Rechte Sidebar (ein-/ausklappbar), PTY (D5) im Working Dir; beim Öffnen
wird der **Autostart-Command aus den Settings** (Default `claude`)
ausgeführt (T0.5). Läuft für macOS; Linux best effort, Windows nein.

### T7 — `ask_bo`-Chat-Elemente (1–2 Tage)
desktop-ui-MCP mit `ask_bo` (D4); Rendering der drei Interaktions-Arten
in der Sidebar (Antwort friert das Element ein, wie iKanbanAi);
`.mcp.json`-Template um desktop-ui erweitert. Vertragstest: Schema-
Fixtures beider Seiten byte-identisch.

### T8 — Wrap-up
Doku (`docs/toolkit.md`: Toolbox-Format, Discovery-Vertrag, Terminal),
dev-up unverändert; Tag-Vorschlag; Rust-Plan-Reststufen (System-CLI,
Distribution) neu bewerten.

## Open Questions (Runde 1 — bitte kurz beantworten)

1. **Reihenfolge bestätigen** (D7): Toolbox+Discovery zuerst, Exec-Port
   danach — oder braucht iKanbanAi zuerst etwas anderes? Was genau
   erwartet iKanbanAi als „Discovery-Client" (nur `tools_list`/
   `actions_propose` übers Netz statt Datei, oder auch `mcp_list`)?
2. **Discovery-Port 8767** ok? Und: soll Discovery zusätzlich stdio
   sprechen (für `claude mcp add` ohne laufende App)?
3. **Toolbox-TOML 1:1** (D1) ok — inkl. `kind: kb`, obwohl
   Knowledgebases funktional erst mit der Rust-CLI/kb-Portierung wieder
   angebunden werden?
4. **Working Dir**: genau EINES global in den Settings (Empfehlung für
   den Start) — oder Liste mehrerer Projekte mit Umschalter?
5. **Terminal-Agent**: Claude Code als gesetzter Agent bestätigen
   (Templates in T1 sind darauf zugeschnitten)? Auto-Start beim Öffnen
   der Sidebar oder nur manuell?
6. **`ask_bo`-Antwort-Timeout**: Tool-Call blockiert bis Antwort — soll
   es einen Timeout/„später beantworten"-Pfad geben (iKanbanAi-Semantik
   übernehmen)?
7. **Parallels**: aktuell aktiv im Einsatz? Sonst schiebe ich T5 hinter
   T6/T7.
8. **Einweisung-Templates** (D6): reicht das Trio CLAUDE.md + .mcp.json
   + .claude/settings.json? Gewünschte Inhalte für CLAUDE.md im Working
   Dir (Speccify-Kurzkontext + Verweis auf Discovery-MCP)?

## Risiken

- **Zwei ask_bo-Implementierungen driften** (iKanbanAi in-process vs.
  Desktop-MCP) → Schema-Fixtures als geteilter Vertragstest (T7).
- **Discovery-Sync mit iKanbanAi** (lokaler Store ↔ Discovery) ist die
  einzige echte Schnittstellen-Änderung drüben — früh abstimmen (T3).
- **PTY/Terminal-Scope-Kriechen** (Tabs, Splits, Themes…) — MVP: EIN
  Terminal, EIN Working Dir.
- Exec-Umschaltung auf 8765 nur nach Harness-Parität + den drei
  Lebensdauer-Tests (wie im Rust-Plan festgeschrieben).
