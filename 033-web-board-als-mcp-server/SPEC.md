---
station: Doing
order: 14
created: 2026-09-13
needs_human: true
ready: false
open_question: null
parent: null
---
# Web-Board stellt einen MCP-Server bereit

## Why

Der erste Integrationsschritt mit itsdcloud: itsdcloud kann externe
Streamable-HTTP-MCP-Server je Projekt als Werkzeug-Integration installieren
(itsdcloud-Spec 0030/0032). Stellt jedes Web-Board (Spec 032) einen MCP
bereit, sieht der PO das Board sofort im Projekt-Chat und später in einer
Ansicht — ohne neuen Datenpfad. [Integrationsplaybook](../../playbooks/itsdcloud-integration.md), Phase 1.

## What

Der Board-Dienst `speccify-board` hängt unter `/mcp` einen MCP-Server
(FastMCP, Streamable HTTP, JSON-Antworten, zustandslos) ein, der dieselbe
Registry nutzt wie die Seiten. Tools: `board_summary`, `list_repos`,
`list_specs(repo?, station?, owner?, query?)`, `get_spec(repo, spec_id)`,
`who_works_on_what`, `move_station(repo, spec_id, station)`,
`toggle_task(repo, spec_id, index, done)`, `refresh`. Ressourcen
`board://summary` und `board://<repo>/<spec_id>`. Antworten sind
`{ok, …}`-Objekte mit Fehlercode statt Ausnahme. Zugang per
`Authorization: Bearer <BOARD_MCP_TOKEN>` (Umgebung); ohne Token offen.
Basic-Auth des Boards (`BOARD_PASSWORD`) gilt nicht für `/mcp` — dort zählt
der Token. Vertrag im Playbook, Kapitel „Board-MCP“.

Nicht enthalten: Anlegen von Specs, Textbearbeitung, itsdcloud-seitige
Änderungen (034), Nutzer je Aufruf (ein Token je Board).

## Acceptance

- Wenn ein MCP-Client `initialize` und `tools/list` gegen `/mcp` ruft, dann
  antwortet der Dienst mit den acht Tools und deren Schemas; ohne gültigen
  Token (falls gesetzt) mit 401.
- Wenn `list_specs` mit `station: Doing` gerufen wird, dann entspricht die
  Antwort den Karten der Doing-Spalte aller Repos (Nummer, Titel, Besitzer,
  Branch, Tasks); `repo` grenzt ein.
- Wenn `move_station` oder `toggle_task` gerufen wird, dann entsteht derselbe
  Commit wie über die HTTP-API (Autor, History-Zeile `board`), und die
  Antwort nennt den Commit; Fehler (unbekannte Spec, Konflikt) kommen als
  `{ok: false, code, message}`.
- Wenn itsdcloud den Server als Integration installiert (`probe`), dann sind
  alle Tools sichtbar und abwählbar; der Projekt-Chat beantwortet „wer
  arbeitet woran“ mit den Daten des Boards (manuelle Prüfung).

## Decisions

- D1, 2026-09-13: FastMCP aus dem `mcp`-SDK, im selben Prozess wie das
  Board (`streamable_http_app` unter `/mcp`), damit Registry, Klone und
  Schreibpfad geteilt bleiben.
- D2, 2026-09-13: Tools spiegeln die HTTP-API; keine zweite Logik.
  Schreibende Tools bleiben im Standard aktiv, weil itsdcloud sie je Projekt
  abwählen kann; Empfehlung im Playbook.
- D3, 2026-09-13: Ein Token je Board-Instanz; personenbezogene Identität kommt
  später mit dem Nutzerkonzept (nicht Teil dieser Spec).

## Tasks

- [ ] MCP-Server im Board-Dienst: Tools, Ressourcen, Fehlercodes, Bearer-Prüfung.
- [ ] Mount unter `/mcp` neben den Seiten; CLI/Env `BOARD_MCP_TOKEN`; Docker/Compose ergänzt.
- [ ] Tests: Handshake, `tools/list`, `list_specs`/`get_spec`, Schreib-Tools mit Commit, 401.
- [ ] `docs/web-board.md` und Playbook-Vertrag abgleichen; itsdcloud-Einrichtung Schritt für Schritt.
- [ ] Manuell: Board als MCP-Integration in einem itsdcloud-Projekt installieren, Frage im Chat stellen.

## Verification

Noch nichts geprüft.

## Questions

Keine.
