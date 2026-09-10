# Exec-MCP — Wire-Kontrakt (Referenz: dotagent `2949d1d`)

Dieser Vertrag ist die Portierungs-Grundlage für `crates/exec-mcp` (Stufe R1
im Plan [`rust-neustart-toolkit-mcps.md`](../.agent/specs/archive/2026-08-04-rust-neustart-toolkit-mcps/SPEC.md)).
Quelle ist die Python-Referenz **dotagent** (`src/dotagent/mcp/{server,exec_tool,allowlist}.py`,
Commit `2949d1d`); Kontrakt-Gegenseite ist die Mac-App **iKanbanAi**
(`ExecStreamClient.swift`). **Der Rust-Port übernimmt alle Semantiken und
Fehlertexte wörtlich** — nur `serverInfo.name`/`version` und das GET-Banner
dürfen abweichen (der Diff-Harness normalisiert genau diese Felder).
Seit Spec 014 ergänzt der Rust-Port davor die unten beschriebene lokale
HTTP-Sicherheitsgrenze. Erfolgreiche RPC-/SSE-Nutzlasten bleiben unverändert;
unsichere oder übergroße HTTP-Anfragen müssen nicht referenzkompatibel sein.

## Lokale HTTP-Sicherheitsgrenze (Rust)

Gilt gemeinsam für Exec, Discovery, Parallels und Desktop-UI, vor Banner,
JSON-RPC und `/stream`:

- `Host` genau einmal: `127.0.0.1:<Listen-Port>` oder `localhost:<Listen-Port>`
  (Groß-/Kleinschreibung des Namens egal). Nur bei Port 80 darf die Portangabe
  fehlen. Fremde Namen/Ports, fehlende oder doppelte Hosts → **403**.
  Proxy-Header ersetzen die Prüfung nicht; Bindung bleibt IPv4-Loopback.
- Die Browser-Origin-Allowlist ist leer. Jeder `Origin`-Header → **403**, auch
  `null`, leer und localhost. Keine CORS-Freigabe/Preflight-Ausnahme. Native
  Clients senden keinen Origin. Eine neue Browserintegration benötigt zuerst
  einen expliziten Sicherheitsvertrag; Loopback allein ist keine Freigabe.
- Nur `GET` (bestehendes Banner) und `POST`; sonst **405**, `Allow: GET, POST`.
- `POST` braucht genau einen `Content-Type: application/json` (Parameter wie
  `charset=utf-8` erlaubt), sonst **415**. Damit werden auch einfache
  Browser-Formular-/Textanfragen nicht als RPC interpretiert.
- Maximal **1 MiB Anfragekörper**, auch bei `Transfer-Encoding: chunked`;
  größere deklarierte/empfangene Bodies → **413**. Grenze gilt nicht für
  SSE-Ausgaben. Ungültiges/mehrdeutiges Framing oder verkürzte Bodies → **400**.
- Transportfehler enthalten `{"error":{"code":"…","message":"…"}}`;
  ungültiges JSON behält den unten beschriebenen JSON-RPC-Parsefehler.

Dies erfüllt die für diesen Ausbau gewählte Host-/Origin-/Body-Grenze,
nicht vollständige MCP-Konformität oder Authentifizierung. Andere lokale
Programme können ohne Origin weiter zugreifen; Exec-Allowlist bleibt wichtig.
GET liefert aus Kompatibilitätsgründen weiterhin das historische Banner, keinen
MCP-GET-Stream. Header-Timeouts, Verbindungslimits und Schutz gegen langsame
Clients sind nicht Gegenstand dieser Änderung. stdio bleibt unverändert.

Grundlage: [MCP-Transport 2025-03-26, Security Warning](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports).
Prüfung: `cargo test -p speccify-mcp-core` und der reine Lese-Smoke-Test
`python scripts/test_mcp_http_boundary.py --url http://127.0.0.1:18768 --expect-server speccify-desktop-ui-mcp`.

## HTTP-Layer

- Nur `127.0.0.1`, ein Port (Referenz-Default **8765**).
- `GET <beliebig>` → `200 text/plain`, Banner (Referenz: `dotagent exec-mcp`;
  Rust-Port: eigenes Banner — normalisiert).
- `POST <beliebig>` mit JSON-Body → JSON-RPC (Pfad egal), **außer** der Pfad
  endet (nach `rstrip("/")`) auf `stream` → SSE-Streaming (s. u.).
- Body kein gültiges JSON → `400` mit
  `{"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":"Parse error"}}`.
- JSON-RPC-**Notification** (ohne `id`, z. B. `notifications/initialized`)
  → `202`, leerer Body.

## JSON-RPC (Streamable HTTP, protocolVersion `2025-03-26`)

| Methode | Ergebnis |
|---|---|
| `initialize` | `{"protocolVersion":"2025-03-26","capabilities":{"tools":{}},"serverInfo":{"name":…,"version":…,"mode":"bound"\|"multi"[,"projectRoot":"<abs>"]}}` — `projectRoot` nur im bound-Modus. |
| `tools/list` | `{"tools":[…]}` — 3 Deskriptoren (`run_command`, `run_action`, `list_actions`), Beschreibungstexte und `inputSchema` wörtlich wie Referenz; `required` hängt vom Modus ab (multi: `project` zusätzlich Pflicht). |
| `tools/call` | Tool-Ergebnis (s. u.). |
| sonst | `{"error":{"code":-32601,"message":"Unbekannte Methode: <method>"}}`. |

Tool-Ergebnisse haben immer die Form
`{"content":[{"type":"text","text":<string>}],"isError":<bool>}`.

## Modi & Projekt-Auflösung

- **bound** (`--project <root>`): `project`-Argument optional; ein fremder
  Pfad wird abgelehnt: `Server ist an <root> gebunden — 'project' '<raw>' wird abgelehnt.`
- **multi** (ohne `--project`; so läuft der Server unter der Dashboard-App):
  `project` ist **pro Aufruf Pflicht** (absoluter Pfad, muss `.agent/`
  enthalten). Fehlertexte wörtlich:
  - fehlend: `Server läuft im Multi-Projekt-Modus: 'project' (absoluter Pfad des Ziel-Projekts) ist erforderlich.`
  - kein String: `'project' muss ein String (absoluter Pfad) sein.`
  - relativ: `'project' muss absolut sein: '<raw>'`
  - ohne `.agent/`: `Kein dotagent-Projekt (fehlendes .agent/): <pfad>`
    *(Textanpassung „dotagent" → „speccify" ist eine R1-Entscheidung; bis
    dahin wörtlich übernehmen, der Harness vergleicht exakt.)*
- Allowlist/Pending/cwd kommen immer aus dem aufgelösten Projekt;
  Allowlists werden pro Projekt-Root gecacht.

## Tools

### `run_command {command[, project]}`

1. `command` fehlt/leer → Fehler-Result `run_command benötigt 'command' (String).`
2. Projekt auflösen (s. o.).
3. **Allowlist-Check** (s. u.); nicht erlaubt → Pending-Eintrag +
<!-- Fehlertext wörtlich: der Kontrakt verlangt Byte-Gleichheit, ein Umbruch machte ihn falsch. -->
<!-- markdownlint-disable-next-line MD013 -->
   Fehler-Result `Command not allowlisted: "<cmd>". It was recorded for approval — ask the project owner to approve it (pending list in the app), then try again.`
4. Ausführung: `shlex`-Split → **argv ohne Shell**, `cwd` = Projekt-Root,
   Timeout **600 s** (Server-Option `--timeout` übersteuert), stdout/stderr
   getrennt erfasst, je **20 000 Zeichen** gekappt mit Suffix
   `\n… [gekappt nach 20000 Zeichen]`.
5. Ergebnis-Text = JSON-Objekt:
   `{"exit_code":…,"stdout":…,"stderr":…,"truncated":…,"duration_ms":…}`;
   Fehlerfälle: `{"error":"Befehl nicht parsebar: …"|"Leerer Befehl."|"Programm nicht gefunden: <argv0>"|"Timeout nach <T>s.","exit_code":null[,stdout/stderr]}`.
   `isError` = `exit_code != 0`.
6. Nach erfolgreichem Lauf: **Einmal-Freigaben konsumieren**.

### `run_action {name[, project]}`

- `name` fehlt/leer → `run_action benötigt 'name' (String).`
- Lookup in `.agent/actions.json` (Format: [`schema/actions.schema.json`](../schema/actions.schema.json)).
- Unbekannt → `Unknown action "<name>". Known actions: <sortiert, komma-getrennt|(none)>. Use list_actions for details.`
<!-- Fehlertext wörtlich: der Kontrakt verlangt Byte-Gleichheit, ein Umbruch machte ihn falsch. -->
<!-- markdownlint-disable-next-line MD013 -->
- `confirmed: false` → `Action "<name>" is not confirmed yet — ask the project owner to confirm it in the Actions tab, then try again.`
- Ohne `command` → `Action "<name>" has no command.`
- Sonst: Delegation an den `run_command`-Pfad (inkl. Allowlist!).

### `list_actions {[project]}`

Gibt den **rohen Dateiinhalt** von `.agent/actions.json` als Text zurück;
Datei fehlt → `[]`.

## Allowlist (Sicherheitsmodell)

- `.agent/exec-allowlist.json`: Array `{"pattern": str, "permanent": bool=true}`.
- Matching: **Token-Präfix** über `shlex`-Tokens — `npm test` erlaubt
  `npm test --watchAll=false`, nicht `npm testfoo`, nicht `npm install`.
- `permanent: false` = Einmal-Freigabe, wird nach passendem Lauf entfernt.
- `.agent/exec-pending.json`: abgelehnte Befehle als
  `{"command": str, "requested_at": "<UTC %Y-%m-%dT%H:%M:%SZ>"}`,
  **dedupliziert nach Befehlstext**. Beide Dateien: `indent=2`,
  `ensure_ascii=False`, abschließender `\n`.

## `POST …/stream` (SSE — iKanbanAi-Ausgabefenster)

Request-Body: `{"command": "...", "project": "<abs. Pfad>"}` (kein JSON-RPC).
Nach bestandener HTTP-Eingangsprüfung Antwort `200`, `Content-Type: text/event-stream`, `Cache-Control: no-cache`;
je Event eine Zeile `data: <json>\n\n` (`ensure_ascii=False`), geflusht.

- je Ausgabezeile: `{"type":"line","text":"…"}` — **stderr in stdout
  gemergt** (Konsolen-Reihenfolge), Zeile ohne abschließendes `\n`,
  Decoding-Fehler per Replacement-Char.
- Abschluss: `{"type":"exit","exit_code":…,"duration_ms":…,"truncated":false}` —
  `truncated` bleibt aus Wire-Kompatibilität und ist **immer false**
  (Streaming ist seit `2949d1d` UNGEKAPPT; die 20k-Kappung gilt nur für
  `run_command`, das in den Agent-Kontext geht).
- Fehler vor/statt Ausführung als exit-Event mit `error` und
  `exit_code:null` (Texte wie oben: nicht parsebar / leer / Programm nicht
  gefunden / nicht allowlisted / Projekt-Fehler); Allowlist-Text im Stream:
  `Command not allowlisted: "<cmd>". It was recorded for approval — ask the project owner to approve it, then try again.`
  (ohne „(pending list in the app)" — bewusste Abweichung der Referenz!).
- **Timeout** (600 s): Prozess wird gekillt, exit-Event
  `{"type":"exit","error":"Timeout nach <T>s.","exit_code":null,"duration_ms":…,"truncated":false}`.
- **Stop-Semantik**: bricht der Client die Verbindung ab (Disconnect),
  wird der Kindprozess **sofort gekillt und gereapt** (kein Weiterlaufen
  bis zum Timeout, kein Zombie).
- Clients überspringen unbekannte Event-Typen tolerant — Erweiterungen
  erlaubt, Umbenennungen nicht.
- Client-Fallback (iKanbanAi): antwortet `/stream` nicht mit `200`, nutzt
  der Client das JSON-RPC-Tool `run_command`.

## Portierungs-Checkliste (dotagent-Tests, 23 Fälle)

`tests/mcp/test_server.py`: initialize+notification · tools_list ·
call_allowed_command · denied_records_pending · list_actions_reads_json ·
run_action_executes_confirmed · run_action_rejects_unknown_and_unconfirmed ·
run_action_respects_allowlist · unknown_method_rpc_error ·
bound_rejects_foreign_project · multi_initialize_reports_mode ·
multi_tools_list_requires_project¹ · multi_call_without_project_fails ·
multi_rejects_dir_without_agent · multi_allowlists_per_project ·
multi_list_actions_per_project — ¹ prüft das `required`-Feld der Deskriptoren.

`tests/mcp/test_stream.py`: lines_then_exit · merges_stderr_and_exit_code ·
not_allowlisted_records_pending · multi_requires_and_uses_project ·
close_kills_child_process · timeout_kills_process ·
default_cap_exceeds_run_command_cap · command_is_not_capped.

## Kontrakt-Diff-Harness (`scripts/exec_mcp_contract.py`)

Schickt eine Szenario-Batterie an **Referenz** und **Kandidat** und difft
die normalisierten Antworten (normalisiert: `duration_ms`, `requested_at`,
`serverInfo.name/version`, GET-Banner, Projekt-Pfade). Jede Seite bekommt
ihr **eigenes** frisches Fixture-Projekt (Allowlist + actions.json), damit
sich Pending-Schreibzugriffe nicht mischen; die Datei-Effekte
(exec-pending.json) werden pro Seite mitverglichen. Beide Server müssen im
**Multi-Modus** laufen.

```bash
# Referenz (dotagent, Python):
cd ~/Desktop/Work/Articles/dotagent && uv run dotagent mcp serve --port 8765
# Kandidat (Rust, ab R1) auf eigenem Port:
cargo run -p speccify-exec-mcp -- --port 8865

# Diff (Exit 0 = Parität):
uv run python scripts/exec_mcp_contract.py \
  --reference http://127.0.0.1:8765 --candidate http://127.0.0.1:8865

# Nur Referenz inspizieren (Selbsttest/Erwartungswerte):
uv run python scripts/exec_mcp_contract.py --reference http://127.0.0.1:8765
```

Nicht im Harness (Prozess-Lebensdauer statt Request/Response — als
Rust-Integrationstests in R1 nachbauen): Timeout-Kill, Disconnect-Kill
(Stop-Semantik), Ungekapptheit sehr großer Streams. **Umschalt-Regel:**
erst wenn der Harness grün ist UND diese drei R1-Tests stehen, übernimmt
der Rust-Server Port 8765 — nie beide gleichzeitig auf 8765.
