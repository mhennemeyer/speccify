# Speccify — Agent-Einweisung (Working Dir)

Dieses Verzeichnis ist das Working Dir der Speccify-Desktop-App. Hier
entstehen eigene Tools, MCP-Manifeste und Aktionen; der Terminal-Agent
der App startet in diesem Verzeichnis.

## Was ist Speccify?

Eine Spec-First-Plattform: Komponenten werden als `speccify.yaml`-Specs
beschrieben (Verhalten, API-Vertrag, Komposition) — AI-Agents generieren
daraus deterministisch Code für React/SwiftUI/Angular. Der visuelle
Composer der Desktop-App editiert solche Specs.

## Werkzeuge (MCP-Server, siehe .mcp.json)

- **speccify-discovery** (`http://127.0.0.1:8767`): erster Anlaufpunkt.
  `mcp_list` liefert alle verfügbaren MCP-Server inkl. fertiger
  Client-Config; `tools_list` liefert Toolbox-Einträge und die
  Aktionslisten (global + Working Dir). Eigene Vorschläge über
  `actions_propose`; neue Tool-/MCP-Manifeste über `scaffold`.
- **speccify-exec** (`http://127.0.0.1:8765`): führt freigegebene
  CLI-Befehle projektgebunden aus (`run_command`, `run_action`,
  `list_actions`). Nicht freigegebene Befehle landen als
  Pending-Request zur Freigabe in der App — erwähnen und weiterarbeiten,
  nicht sofort erneut versuchen.
- **speccify-desktop-ui** (`http://127.0.0.1:8768`, läuft nur solange die
  Speccify-App offen ist): `ask_bo` stellt dem Owner eine Frage mit
  UI-Element — `buttons` (Einzelauswahl), `multi_select` (Checkboxen),
  `form` (Fragenliste; leere Eingabe = empfohlener Wert gilt). Der Call
  wartet auf die Antwort; bei Timeout bleibt die Frage offen — mit
  `ask_bo_result` nachfragen statt erneut stellen. Nutze das für
  Entscheidungen statt langer Freitext-Rückfragen.
- **playwright**: Browser-Automation (stdio, wird bei Bedarf gestartet).

## Konventionen in diesem Verzeichnis

- Aktionen: `.agent/actions.json` (benannte CLI-Befehle; Schema siehe
  Speccify-Repo `schema/actions.schema.json`).
- Eigene Tools/MCPs: `.speccify/toolbox/*.toml` (dotagent-kompatible
  Manifeste: `kind = "tool" | "mcp" | "kb"`, optional `[run]`).
