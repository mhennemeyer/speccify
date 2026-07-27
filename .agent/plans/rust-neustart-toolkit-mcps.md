---
isActive: false
---

# Plan: Migration nach Rust — Toolkit & MCPs (aus dotagent)

> **2026-07-25:** Die Ausführung von R1/R2 (+ Parallels/Playwright,
> Toolbox, Terminal) läuft jetzt über den aktiven Plan
> [`toolkit-discovery-terminal.md`](./toolkit-discovery-terminal.md)
> (BO-Zielvorgabe, dort Stufen T2–T5). Dieses Dokument bleibt die
> **Kontrakt-/Referenz-Quelle** (Wire-Vertrag, dotagent-/iKanbanAi-
> Referenzen, Umschalt-Regeln); R3/R5 (System-CLI, Distribution)
> werden nach T8 neu bewertet.

**Angelegt 2026-07-24 nach BO-Richtungsentscheidung. Dieses Dokument ist
die vollständige Einweisung für Sessions, die in diesem Repo starten und
kein dotagent-Vorwissen haben — alles Nötige steht hier oder ist verlinkt.**

> **Umpriorisierung (BO, 2026-07-24, später am Tag):** Die App-Übernahme
> (ehem. R3) und die Composer-Integration (ehem. R4) sind in den eigenen,
> VORgezogenen Plan [`desktop-app-und-composer.md`](./desktop-app-und-composer.md)
> gewandert und laufen zuerst — die App zieht mit der bestehenden
> dotagent-CLI-Bridge um. Dieser Plan ist damit die nachgelagerte
> **Rust-Migration** (Exec-MCP, Discovery-MCP, System-CLI, Umschaltung,
> Distribution). **R0 ist geliefert** (siehe unten); R1 startet erst nach
> Plan „Desktop-App & Composer" A0/A1.

## Worum es geht (Kurzfassung)

Speccify bekommt eine **Desktop-/Infrastruktur-Schicht in Rust**:
Tools/Aktionen werden hier definiert, in Rust implementiert und **via MCP
bereitgestellt** — ein **Exec-MCP** führt sie aus, ein neuer
**Discovery-MCP** macht sie (und andere MCPs) für Agents auffindbar.
Vorlage und Referenzimplementierung ist das Projekt **dotagent**
(`~/Desktop/Work/Articles/dotagent`), das dafür **nicht** migriert,
sondern in Rust **neu geschrieben** wird. dotagent bleibt als Referenz
stehen und wird nach dem Umstieg archiviert.

## Hintergrund: Was ist dotagent?

Eine Python-Toolbox des BO (MIT, OSS-safe bereinigt, Commit `583ae11`
dort; **einziger Nutzer ist der BO** — daher keine Kompatibilitätslast):

*   **Exec-MCP** (`src/dotagent/mcp/`): JSON-RPC-Server auf Port 8765,
    führt CLI-Befehle projektgebunden aus; seit Commit `8f1806e` mit
    SSE-Streaming-Endpoint `POST /stream`, seit Commit **`2949d1d`**
    (der maßgebliche Referenzstand) mit 600-s-Timeout, ohne
    Output-Kappung im Stream und mit Stop-Button-Semantik.
*   **Tauri-2-Dashboard-App** (`app/dashboard`): Bibliothek/Umgebung/
    Server/Knowledgebases-Tabs, Prozess-Supervisor
    (`spawn_process`/`kill_process` + Log-Streaming). Bereits Rust/TS —
    das einzige Stück, das **direkt umzieht** (→ `apps/desktop`).
*   CLI (`dotagent registry|doctor|mcp|kb|python`), plus private
    Experimente (web/analytics/envoy/vision/beuys — sterben, ziehen nie um).
*   Arbeitsstand dort: `.agent/kontext.md` (untracked); Spiegel-Plan aus
    dotagent-Sicht: `.agent/plans/speccify-merge.md` (untracked).

**Erster externer Client:** die Mac-App **iKanbanAi**
(`~/Desktop/Work/iKanbanAi`, privates Repo) spricht den Exec-MCP heute
direkt an — Aktionsliste pro Projekt, Ausführung über `/stream`.

## Die Entscheidung (BO, 2026-07-24)

1.  **Keine Python-Pakete mehr** fürs Toolkit: kein PyPI-Release, kein
    Paket-Merge. (Randnotiz: PyPI-Name `speccify` gehört ohnehin Lyst
    Ltd., inaktiv seit 2021 — durch die Entscheidung irrelevant.)
2.  Tools werden **in Speccify definiert, in Rust geschrieben**, via
    **MCP bereitgestellt**.
3.  **Discovery-MCP** (neu): Agents entdecken darüber alle vorhandenen
    Tools/Aktionen und weitere MCPs. Erster Client: iKanbanAi-Aktionsliste.
4.  Ausführung der Aktionen über den **Exec-MCP** (Rust-Nachbau).
5.  **Nutzer können eigene Aktionen anlegen** — Aktionen sind Daten,
    nicht Code (Schema unten).
6.  **Kein App Store, kein Sandboxing.** Distribution direkt:
    Developer-ID-Signing + Notarisierung + Tauri-Updater, Download über
    speccify.io. Unsandboxed ist Voraussetzung für Exec/Supervisor.
7.  **Sauberer Neustart statt Umzug**: dotagent = Referenz, keine
    Historien-/Subtree-Übernahme.

## Abgrenzung Rust ↔ Python (wichtig, Scope-Schutz)

„Kein Python mehr" gilt für das **Toolkit**. Die Speccify-Engine
(`core/`, `cli/`, `mcp/` in diesem Repo) und das Composer-Backend
(FastAPI, `apps/web`) **bleiben Python** und laufen künftig als von der
Desktop-App verwaltete Prozesse. Schnitt:

*   **Rust:** Exec-MCP, Discovery-MCP, Desktop-App (`apps/desktop`),
    dünne System-CLI (Server-Start/Stop, env doctor).
*   **Python:** Spec-Engine, speccify-mcp, Composer-/Web-Backend.

## Referenzen (wo nachschauen)

| Was | Wo |
|---|---|
| Exec-MCP-Referenzimplementierung | dotagent `src/dotagent/mcp/exec_tool.py` + `server.py`, Stand Commit `2949d1d` |
| Portierungs-Checkliste/Spez | dotagent `tests/mcp/test_server.py`, `tests/mcp/test_stream.py` (Teil von 576 Tests gesamt — beim Portieren als Checkliste nutzen, nicht neu erfinden) |
| Stream-Client (Kontrakt-Gegenseite) | iKanbanAi `Packages/iKanbanAiKit/Sources/Workspace/ExecStreamClient.swift` |
| Actions-Schema (Vorlage) | iKanbanAi `Packages/iKanbanAiKit/Sources/AgentStorage/ProjectActionsStore.swift` |
| Tauri-Shell + Supervisor | dotagent `app/dashboard` |
| dotagent-Arbeitsstand | dotagent `.agent/kontext.md` (untracked, lokal) |

## Wire-Kontrakt Exec-MCP (exakt einhalten — iKanbanAi hängt dran)

*   `POST http://127.0.0.1:8765/stream`, Body
    `{"command": "...", "project": "<abs. Pfad>"}` → SSE-Strom:
    *   je Ausgabezeile `data: {"type":"line","text":"…"}`
        (stderr in stdout gemergt),
    *   Abschluss `data: {"type":"exit","exit_code":…,"duration_ms":…,
        "error":…,"truncated":…}`.
    *   Clients überspringen unbekannte Event-Typen tolerant —
        Erweiterungen sind erlaubt, Umbenennungen nicht.
*   Antwortet der Server nicht mit 200, fällt der Client auf das
    MCP-Tool `run_command` zurück (JSON-RPC; `initialize` antwortet mit
    `mode: "multi"`). Alte Server ohne `/stream` antworteten 202.
*   Semantik seit `2949d1d`: Timeout **600 s** (Server killt den
    Prozess), **keine** Output-Kappung im Stream, Stop-Semantik
    (Client kann laufende Befehle abbrechen).

## Aktionen & Discovery — Datenmodell

Eine Aktion ist ein **benannter CLI-Befehl mit Metadaten** (Vorlage:
iKanbanAi-`ProjectAction`, dort produktiv im Einsatz):

```json
{ "name": "Tests", "command": "npm test", "description": "…",
  "source": "agent" | "bo", "confirmed": true,
  "toolbar": false, "shortcut": "cmd-u" }
```

*   `source`/`confirmed` tragen den Vorschlags-Flow: Agents schlagen
    Aktionen vor, der Nutzer bestätigt sie in der UI.
*   Ablage **dateibasiert und nutzereditierbar**: global (z. B.
    `~/.speccify/actions/`) + pro Projekt (z. B.
    `<root>/.agent/actions.json`) — Format wird in R0 festgezurrt,
    abgestimmt mit iKanbanAi.
*   **Discovery-MCP-Tools (MVP):** `actions_list` (global + Projekt),
    `actions_propose` (Agent-Vorschlag), `mcp_list` (vorhandene
    MCP-Server mit Port/Status — heute `dotagent mcp list`).
*   Ausführung: Client nimmt `command` aus der Aktion → Exec-MCP
    (`/stream` bzw. `run_command`).

## Stufen (R = Rust-Neustart; bewusst nicht „P" — die Produkt-Phasen
P0–P6 der Speccify-Roadmap laufen unabhängig weiter)

### R0 — Schnitt & Schema ✅ (2026-07-24)
1.  [x] Cargo-Workspace angelegt (Root-`Cargo.toml`, Toolchain-Pin
    `rust-toolchain.toml` = 1.97.1 + rustfmt/clippy): `crates/exec-mcp` +
    `crates/discovery-mcp` als baubare Skelette (`speccify-exec-mcp`/
    `speccify-discovery-mcp`); CI-Job `rust workspace` (fmt/clippy -D
    warnings/build/test). `mcp-core` erst bei Bedarf.
2.  [x] Actions-Schema festgezurrt: [`schema/actions.schema.json`](../../schema/actions.schema.json)
    — wire-kompatibel zur produktiven iKanbanAi-`ProjectAction`
    (Top-Level-Array; `details` heißt auf dem Draht `description`).
    Ablageorte: Projekt `<root>/.agent/actions.json`, global
    `~/.speccify/actions.json` (gleiches Format; bei Befehls-Kollision
    gewinnt das Projekt; `command` = Identitäts-/Dedup-Schlüssel).
3.  [x] Kontrakt spezifiziert + Diff-Harness gebaut:
    [`docs/exec-mcp-contract.md`](../../docs/exec-mcp-contract.md)
    (vollständiger Wire-Vertrag aus `2949d1d` inkl. Fehlertexten,
    Allowlist-/Pending-Dateiformaten, SSE-Framing, 23-Tests-Checkliste)
    + `scripts/exec_mcp_contract.py` (28 Szenarien, normalisiert
    duration/timestamps/serverInfo/Banner/Pfade, vergleicht auch
    Datei-Effekte). **Verifiziert gegen die laufende dotagent-Referenz:
    Selbsttest + Referenz-vs-Referenz-Parität 28/28 grün.** Timeout-Kill,
    Disconnect-Kill und Ungekapptheit sind bewusst NICHT im Harness —
    das werden R1-Integrationstests im Rust-Crate.

### R1 — Rust-Exec-MCP mit Stream-Parität (1–2 Tage)
1.  Implementierung in `crates/exec-mcp`; Verhalten aus
    `exec_tool.py`/`server.py` (`2949d1d`) übernehmen, dotagent-Tests
    als Checkliste.
2.  Kontrakt-Tests grün gegen die Python-Referenz.
3.  Parallelbetrieb auf eigenem Port; erst bei Parität übernimmt der
    Rust-Server Port 8765 und iKanbanAi/Dashboard werden umgestellt.
    Nie beide gleichzeitig auf 8765.

### R2 — Discovery-MCP MVP (1–2 Tage)
1.  `actions_list` / `actions_propose` / `mcp_list` in
    `crates/discovery-mcp`.
2.  Nutzer-Aktionen: Dateiformat + UI zum Anlegen/Bestätigen (App).
3.  iKanbanAi-Aktionsliste als erster Discovery-Client — Sync-Semantik
    zwischen lokalem Store und Discovery klären.

### R3 — App-Umstellung ✅ (2026-07-27) — dotagent funktional abgelöst
> Zuschnitt angepasst: statt eines separaten Rust-CLI-Binarys (der Name
> `speccify` gehört der Python-Spec-Engine) sind die letzten dotagent-
> Funktionen **native Tauri-Commands** geworden; Server-Start/Stop und
> mcp_list waren schon nativ (Toolkit-Plan T8/T3).
1.  [x] `system_cmd.rs`: `doctor` (Check-Liste bereinigt: pipx/dotagent
    raus, Claude Code rein; PATH+Well-Known-Suche, Symlink-Dedup,
    parallele Version-Probes), `python_list`/`python_install` (uv),
    `kb_list` (liest `~/Knowledgebase/*/data/chunks.json` + faiss-Größe +
    Buch-Pfad-Auflösung). JSON-Formate 1:1 wie `dotagent … --json`;
    **Paritätstest gegen die Referenz grün** (`kb_list_matches_dotagent_
    reference`, #[ignore], 6 echte KBs byte-gleich in Name/Books/Chunks/
    Titeln). `run_dotagent`/`find_dotagent`/`DOTAGENT_BIN` entfernt,
    `lib/dotagent.ts` → `lib/system.ts` (invoke-basiert).
2.  [x] Server-Tab verwaltet die Rust-MCPs (Toolkit-T8); speccify-mcp
    (Python, stdio) wird vom Client gestartet.
> **dotagent wird von Speccify nicht mehr aufgerufen.** Das Repo bleibt
> nur noch als Kontrakt-Referenz (Diff-Harness, Paritätstests) bis R5.

### R5 — Distribution ohne Store (später)
Developer-ID-Signing + Notarisierung, Tauri-Updater, Download-Seite auf
speccify.io. Danach dotagent-Repo archivieren (README-Verweis
„Referenz für die Rust-Portierung") und Restore-Doku/Memories umziehen.

## Risiken & Stolpersteine

*   **Stille Wire-Abweichungen** brechen iKanbanAi leise →
    Kontrakt-Testsuite (R0.3) ist Pflicht, vor jedem Umschalten.
*   **Scope-Kriechen:** Verlockung, kb/agent-Provider/… aus dotagent
    gleich mitzuschreiben — bewusst nur Exec + Discovery + App; Rest on
    demand, dotagent bleibt als Referenz ja stehen.
*   **Zwei Paketwelten im Repo:** uv (Python) + pnpm (JS) + neu cargo —
    CI-Jobs pro Welt sauber trennen; `dev-up.sh` erweitern statt forken.
*   **`.agent/` ist in diesem Repo getrackt** (inkl. Chats) — dotagent
    hat sein `.agent/` vor der OSS-Öffnung untrackt (`583ae11`). Vor
    einer Public-Schaltung dieses Repos gleiches Vorgehen prüfen:
    dieser Plan referenziert private Projekte/Pfade (iKanbanAi, BO-Setup).

## Verhältnis zur laufenden Speccify-Roadmap

Die Produkt-Roadmap (Composer-Verfeinerung P3, API-Harness, P4 Builds,
P5 Git-Quellen — siehe `status.md`) läuft **parallel weiter**; dieser
Plan ist der Infrastruktur-Workstream daneben. Berührungspunkt ist R4
(Composer-Fenster) — dort treffen sich beide.
