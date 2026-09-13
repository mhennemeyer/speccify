---
station: Backlog
order: 16
created: 2026-09-13
needs_human: true
ready: false
open_question: null
parent: null
---
# itsdcloud-Gedächtnis und Chat im Speccify-Terminal

## Why

Der Agent im Speccify-Terminal soll in Echtzeit wissen, was im
itsdcloud-Projekt passiert: Gedächtnis, Entscheidungen, Dokumente und was der
PO vor einer Minute im Chat geschrieben hat — ohne Copy/Paste, mit sichtbarer
Quelle und Aktualität. [Integrationsplaybook](../../playbooks/itsdcloud-integration.md),
Phase 3; baut auf V1-03 auf.

## What

Ein Speccify-seitiger MCP `speccify-itsdcloud` (Python, stdio; eingetragen in
den Agent-Start wie die anderen Speccify-MCPs) über die bestehende
itsdcloud-REST-API mit persönlichem Token und expliziter Zuordnung
`itsdcloud.project_id` in den Projekt-Settings (Token nur im Rechnerspeicher).
Tools: `whoami`, `project_memory`, `search_memory(query)`, `list_chats`,
`recent_messages(since, chat?)`, `catchup(chat)`, `list_documents`,
`get_document(id)`. Ein lokaler Ereignispuffer abonniert die Projekt-Chats
(SSE/Broker-Ereignisse), damit `recent_messages` neue Nachrichten ohne Polling
liefert. Der Startvertrag (007) lädt beim Auftragsstart Gedächtnis und die
letzten Nachrichten als Kontextdatei und macht das im Projektfenster sichtbar
(Panel „itsdcloud“: Projekt, Stand, letzte Nachricht, offline/veraltet). Kein
ungefragtes `memory/refresh`.

Benötigt in itsdcloud (eigene Spec dort): Token-Weg für Werkzeuge
(persönlicher API-Token oder Device-Flow statt Browser-Login), eine
Ereignisschnittstelle je Projekt (bestehender Broker als SSE für Werkzeuge),
Klärung des Exportumfangs (private Chat-Anteile im Gedächtnis).

Nicht enthalten: Schreiben nach itsdcloud (037), Jira (036), Anzeige der
itsdcloud-Dokumente als Dateien im Speccify-Dateibaum.

## Acceptance

- Wenn ein Projekt einer itsdcloud-Projekt-ID zugeordnet und ein Token
  hinterlegt ist, dann liefert `project_memory` das Gedächtnis mit
  Zeitstempel, und ein neuer Agent-Auftrag hat es ohne Copy/Paste im Kontext.
- Wenn der PO im Projekt-Chat schreibt, dann liefert `recent_messages` die
  Nachricht innerhalb weniger Sekunden mit Autor und Zeit.
- Wenn itsdcloud nicht erreichbar ist, dann zeigen Panel und Tools
  „offline/veraltet“ mit dem letzten Stand statt leerer Antworten.
- Wenn das Projekt falsch zugeordnet ist oder Rechte fehlen, dann ist das im
  Panel sichtbar und kein fremder Kontext gelangt zum Agenten.
- Wenn `memory/refresh` gerufen würde, dann nur auf ausdrücklichen Klick mit
  Kostenhinweis.

## Decisions

- D1, 2026-09-13: MCP als Vertrag, Speccify-seitig gebaut (REST-Adapter), bis
  itsdcloud einen eigenen MCP anbietet; Tools bleiben dann identisch.
- D2, 2026-09-13: Kontextübergabe beim Start über den bestehenden Weg (Datei +
  Host-Option), nicht über einen zweiten Prompt-Mechanismus.
- D3, 2026-09-13: Gedächtnis ist Datenkontext; die Policy sagt dem Agenten,
  dass darin enthaltene Anweisungen keine Aufträge sind.

## Tasks

- [ ] itsdcloud-Spec (Token-Weg, Ereignis-API, Exportumfang) auf Ansage anlegen.
- [ ] `speccify-itsdcloud` MCP: Konfiguration, Tools, Ereignispuffer, Fehlerbilder.
- [ ] Projekt-Settings und Panel „itsdcloud“ in der App; Token im Rechnerspeicher.
- [ ] Startvertrag: Kontextdatei mit Gedächtnis + letzten Nachrichten; Policy-Hinweis.
- [ ] Tests mit itsdcloud-Fixture-Server; Leak-Tests (falsches Projekt, fehlende Rechte).

## Verification

Noch nichts geprüft.

## Questions

Keine.
