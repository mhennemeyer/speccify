# Agent-Toolkit — MCPs, Toolbox, Discovery & Terminal

Der Infrastruktur-Workstream aus
[`toolkit-discovery-terminal.md`](../.agent/specs/archive/2026-08-04-toolkit-discovery-terminal/SPEC.md):
Rust-MCP-Server + Toolbox als Fundament, die Desktop-App als Cockpit.
Herkunft: Rust-Neustart der dotagent-Referenz (Commit `2949d1d`). Seit R3
ruft Speccify dotagent nirgends mehr auf; die verbliebenen Erwähnungen in
Code und Doku sind Herkunftsnachweise. Nur zwei Werkzeuge brauchen das alte
Repo überhaupt noch, und beide sind reine Regressions-Netze: der
Kontrakt-Diff-Harness (`scripts/exec_mcp_contract.py`) und der
`#[ignore]`-Paritätstest für `kb_list`.

## Die Server auf einen Blick

| Server | Port | Transport | Tools | Quelle |
|---|---|---|---|---|
| **speccify-exec** | 8765 | Streamable HTTP + stdio + `POST /stream` (SSE) | `run_command`, `run_action`, `list_actions` | `crates/exec-mcp` |
| **parallels-dotnet** | 8766 | Streamable HTTP + stdio | `vm_list/status/start/stop/exec` (.NET in der Windows-VM) | `crates/parallels-mcp` |
| **speccify-discovery** | 8767 | Streamable HTTP + stdio | `mcp_list`, `tools_list`, `actions_propose`, `scaffold` | `crates/discovery-mcp` |
| **speccify-desktop-ui** | 8768 | Streamable HTTP (nur solange die App läuft) | `ask_bo`, `ask_bo_result` | App-Prozess (`apps/desktop`) |
| **playwright** | – | stdio (Client startet `npx @playwright/mcp`) | Browser-Automation | Toolbox-Manifest |
| **speccify-mcp** | – | stdio (`uv run speccify-mcp` im Repo) | Playbook-Engine (`playbook_*`, `search`, `lock`/`pull`/`verify`, Viewer-Brücke) | `mcp/` (Python) |

Alle Server binden ausschließlich `127.0.0.1`.

- **Exec-Vertrag** (wire-identisch zur dotagent-Referenz, Diff-Harness
  28/28): [`exec-mcp-contract.md`](./exec-mcp-contract.md). Erster
  externer Client: iKanbanAi.
- **Discovery** ist der Einstiegspunkt für Agents: `mcp_list` liefert
  jeden Server inkl. Client-Config und Laufzeitstatus; `tools_list` liefert Toolbox-Tools und
  die Aktionslisten (global + Projekt); `actions_propose` legt
  Agent-Vorschläge an (`source=agent`, `confirmed=false`, Dedup nach
  `command`); `scaffold` erzeugt neue Toolbox-Manifeste.
- **ask_bo** (desktop-ui): Frage mit UI-Element — `buttons`
  (Einzelauswahl), `multi_select` (Checkboxen), `form` (Fragenliste;
  leere Eingabe ⇒ empfohlener Wert). Der Call blockiert bis zur Antwort
  in der App-Sidebar; nach Timeout (Default 300 s) bleibt die Frage offen
  und wird per `ask_bo_result` abgeholt. Speccify definiert das Schema; Client-Apps wie iKanbanAi implementieren
  `ChatInteraction`.

## Binaries bauen/installieren

Die gebaute App **bringt die drei MCP-Binaries als Sidecars mit**
(`Speccify.app/Contents/MacOS/`, Plan `r5-distribution.md` R5.1) — für die
verteilte App ist keine Rust-Toolchain und kein `cargo install` nötig. Die
App löst ein Kommando in dieser Reihenfolge auf: **mitgeliefert > PATH >
nicht gefunden**; der Server-Tab zeigt die Quelle pro Server an.

```bash
# Alles auf einmal (idempotent: Deps, Sidecars, Engine-Payload, Start):
./scripts/dev.sh                 # tauri dev
./scripts/dev.sh --release       # .app/.dmg bauen und öffnen

# App inkl. Sidecars bauen (baut die Crates vorher in --release):
pnpm run desktop:build           # → target/release/bundle/macos/Speccify.app
pnpm run desktop:sidecars        # nur die Sidecars neu bauen

# im Speccify-Repo einzeln (rust-toolchain.toml pinnt die Version):
cargo build --release            # → target/release/speccify-*-mcp

# optional dauerhaft in den PATH (Terminal-Nutzung, `tauri dev`-Fallback):
cargo install --path crates/exec-mcp
cargo install --path crates/discovery-mcp
cargo install --path crates/parallels-mcp
```

Server einzeln starten (Beispiele):

```bash
speccify-exec-mcp                     # :8765, multi-Modus
speccify-exec-mcp --project <root>    # bound an ein Projekt
speccify-discovery-mcp                # :8767; Working Dir aus Settings
speccify-discovery-mcp --stdio        # für `claude mcp add` ohne App
speccify-parallels-mcp                # :8766; --project oder Working Dir
```

## Toolbox (Manifeste)

dotagent-kompatibles TOML (`kind = "tool" | "mcp" | "kb"`, optional
`[run] command/args/transport/autostart`, `[requires] binaries`), drei
Quellen — bei Slug-Kollision gewinnt die spezifischste:

1. `<working dir>/.speccify/toolbox/*.toml`
2. `~/.speccify/toolbox/*.toml`
3. builtin (im Binary, `crates/toolbox/builtin/`)

Neue Manifeste: Bibliothek-Tab („+ Neues Manifest"), Discovery-Tool
`scaffold`, oder Datei von Hand anlegen.

## Aktionen

Benannte CLI-Befehle als Daten (`schema/actions.schema.json`,
Speccify definiert das Format, Clients wie iKanbanAi lesen es): pro Projekt `.agent/actions.json`, global
`~/.speccify/actions.json`. Agents schlagen per `actions_propose` vor
(unbestätigt), ausgeführt wird über `run_action` des Exec-MCP —
Sicherheitsmodell ist die Token-Präfix-Allowlist
(`.agent/exec-allowlist.json` + Pending-Freigabe).

## Desktop-App als Cockpit

- **Settings**: EIN globales Working Dir (`~/.speccify/settings.json`),
  Terminal-Autostart-Command mit Claude-/Codex-/Shell-Presets und
  Agent-Einweisungs-Dateien per Klick. `.agent/agent.md` ist kanonisch;
  `CLAUDE.md` und `AGENTS.md` verweisen darauf. MCP-Konfiguration wird nativ
  als `.mcp.json` und `.codex/config.toml` angeboten — niemals überschreibend.
- **Bibliothek**: alle Toolbox-Manifeste (builtin/global/working dir) mit
  Requirements-Badges + Scaffold.
- **Server**: Toolbox-MCPs mit Laufzeitstatus (Port-Probe), Start/Stop
  über den App-Supervisor (Logs live), Client-Config zum Kopieren. Pro
  Server steht, woher sein Binary kommt (mitgeliefert / Python-Engine /
  PATH); die Client-Config nennt den aufgelösten absoluten Pfad, weil ein
  MCP-Client stdio-Server ohne den PATH der App startet.
- **Umgebung**: Doctor-Checks, Python-Versionen via uv — und die
  **mitgelieferte Python-Engine** (siehe unten).
- **⌨ Terminal**: echtes PTY (Login-Shell) im Working Dir; der frei wählbare
  Autostart-Command wird vorgetippt. ⌘C kopiert die
  Selektion, ⌘V fügt ein.
- **ask_bo-Sidebar**: Fragen erscheinen automatisch (auch nach Reload —
  die UI synct offene Fragen aktiv); Tastatur: Pfeile/Enter/Ziffern,
  Space bei Checkboxen, Enter springt im Formular weiter.

Projektfenster und Terminal sind auf macOS und Windows verifiziert.

## Python-Engine der App (ohne Repo)

Playbook-Engine und Web-Backend sind Python. Damit die verteilte App
ohne Repo-Checkout auskommt (Plan `r5-distribution.md`, R5.2), bringt sie
einen **Payload** mit — die vier eigenen Wheels, die aus `uv.lock`
exportierten Third-Party-Pins, die gebaute Viewer-SPA sowie die
Referenz-Playbooks:

```bash
./scripts/build_engine_payload.sh      # vor pnpm run desktop:build
```

Umgebungs-Tab → **„Engine installieren"** baut daraus per `uv` eine venv
unter `~/Library/Application Support/io.speccify.desktop/engine/venv`
(Live-Log in der Karte). Das braucht **einmal Netz**: uv lädt die
Third-Party-Wheels und, falls kein passendes Python 3.12 auf dem System
liegt, auch den Interpreter. Ein Hash-Marker (`installed.json`) erkennt
nach einem App-Update, dass neu installiert werden muss.

**`uv` selbst bringt die App mit** (`scripts/fetch_uv.sh` lädt die
gepinnte Version gegen die veröffentlichte SHA256 und legt sie als
vierten Sidecar ab). Ein systemweit installiertes `uv` ist damit keine
Voraussetzung mehr; das Bundle wird dadurch rund 38 MB größer. Gesucht
wird das App-Bundle **vor** dem PATH — ein älteres `uv` aus Homebrew
überstimmt das mitgelieferte also nicht.

Daraus bedienen sich:

- **Viewer** — ohne Repo-Angabe startet das Backend aus der Engine, mit
  Playbooks und SPA aus den App-Resources. Ein angegebenes Repo mit `.venv`
  und Viewer-Build gewinnt (Dogfooding am Quellstand).
- **speccify-mcp** — das Manifest `uv run speccify-mcp` wird auf
  `<venv>/bin/speccify-mcp` abgebildet, sobald die Engine steht.

## Typischer Flow (Claude oder Codex im Working Dir)

1. Settings → Working Dir wählen, Einweisungs-Dateien anlegen.
2. ⌨ Terminal öffnen → Claude oder Codex starten. Claude liest `.mcp.json`,
   Codex `.codex/config.toml`; beide sehen dieselben Skills aus `.agent/skills`.
3. Agent orientiert sich über Discovery (`mcp_list`/`tools_list`),
   führt Befehle über Exec aus (Allowlist!), stellt Entscheidungsfragen
   über `ask_bo`, schlägt wiederkehrende Befehle per `actions_propose`
   als Aktionen vor.
