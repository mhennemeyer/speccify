---
station: Doing
order: 15
created: 2026-09-13
needs_human: true
ready: true
open_question: null
parent: null
---
# Das Board in itsdcloud: Integration, Chat-Tools, Ansicht

## Why

Der PO soll in itsdcloud sehen, wer an welchen Aufgaben arbeitet — Specs,
Stationen, Fortschritt, Besitzer, Branch — und den Projekt-Chat danach fragen
können. Grundlage ist der Board-MCP aus [033](../033-web-board-als-mcp-server/SPEC.md).
[Integrationsplaybook](../../playbooks/itsdcloud-integration.md), Phase 2.

## What

Diese Spec beschreibt die Speccify-Seite des Vertrags und die Anforderungen
an itsdcloud; die Umsetzung in itsdcloud bekommt dort eine eigene Spec
(nur auf Ansage im itsdcloud-Repo anlegen).

Stufe A (ohne itsdcloud-Code): Board-URL und Token im itsdcloud-Projekt als
„MCP-Server“-Integration eintragen; Tools auswählen (lesend); der Chat-Agent
beantwortet Fragen zum Board. Speccify liefert dafür eine Einrichtungs-
Anleitung mit Screenshots und eine empfohlene Tool-Auswahl.

Stufe B (itsdcloud-Code): Katalogeintrag „Speccify Board“ (Icon, Beschreibung,
Standard-Tools lesend, Feld für Board-URL) und eine Projektansicht „Board“,
die `board_summary` und `list_specs` rendert: Kennzahlen, drei Spalten,
Fortschritt, Besitzer-Initialen, Branch, Flags; Link auf das Web-Board; Stand
und Fehler je Repo sichtbar. Optional Stufe B2: Portal-Push (Contract G) des
Board-Servers, damit Projekte ihn ohne URL installieren.

Nicht enthalten: Schreiben aus der itsdcloud-Ansicht (Chat-Tools können es,
wenn ausgewählt), Jira (036), Echtzeit-Aktualisierung der Ansicht (Reload).

## Acceptance

- Wenn ein itsdcloud-Projekt den Board-MCP als Integration installiert hat,
  dann beantwortet der Projekt-Chat „wer arbeitet gerade woran?“ mit Personen,
  Specs und Branches aus dem Board, und „was ist bereit zur Abnahme?“ mit den
  `ready`-Specs.
- Wenn der Katalogeintrag existiert, dann braucht die Einrichtung nur URL und
  Token; die Tool-Auswahl ist standardmäßig lesend.
- Wenn die Ansicht „Board“ geöffnet wird, dann zeigt sie denselben Stand wie
  das Web-Board (Stichprobe: gleiche Zahlen je Station) und nennt den
  Register-Commit je Repo; ist das Board nicht erreichbar, steht das dort.

## Decisions

- D4, 2026-09-16: Nutzerauftrag „danach weiter mit der Integration“ startet nach
  050 diese Spec einschließlich eigener itsdcloud-Umsetzung. Arbeitsbaum
  `/private/tmp/itsdcloud-speccify-board`, Branch `feat/0051-speccify-board`, auf
  aktuellem `origin/master` (`ea54607`). Der geöffnete Workflow-Migrationsbranch
  bleibt erhalten. Master verwendet noch `docs/specs`; die eigene Spec 0051
  folgt dort dem geltenden Format, ohne die separate Workflow-Migration zu mergen.

- D1, 2026-09-13: Ein Vertrag (Board-MCP) für Chat und Ansicht; kein zweiter
  Lesepfad über `board.json`.
- D2, 2026-09-13: Speccify-Spec hält Vertrag und Anleitung; die
  itsdcloud-Umsetzung wird als itsdcloud-Spec geführt und hier verlinkt.
- D3, 2026-09-13 (BO): Stufe B bekommt eine eigene Oberfläche in itsdcloud und
  wird zuerst in einem Feature-Branch des itsdcloud-Repos erprobt. Sie ist der
  Prototyp für ein allgemeines Muster — MCP-Server mit strukturierten Daten
  visuell darstellen —, das nach der Abnahme als eigene itsdcloud-Spec
  generalisiert wird. Leitlinien im Playbook, Abschnitt „Oberfläche in itsdcloud“.

## Tasks

- [x] Einrichtungsanleitung Stufe A in `docs/web-board.md` (Screenshots aus itsdcloud).
- [x] Empfohlene Tool-Auswahl und Beispiel-Fragen dokumentieren; Prüfung im Chat.
  Deterministischer Chat-Tooltest; natürliche Modellantwort bleibt Abnahme.
- [x] itsdcloud-Spec für Katalogeintrag und Board-Ansicht (Stufe B) auf Ansage anlegen; Vertrag zitieren.
- [x] Nach Umsetzung: Stichprobe Zahlen Web-Board ↔ Ansicht.

## Verification

2026-09-16: itsdcloud Spec 0051 implementiert und als Commit `27d7b8f` auf
[`feat/0051-speccify-board`](https://git.itsd-consulting.de/private-ai/app/-/tree/feat/0051-speccify-board)
gepusht. `ci.skip` verhindert die bestehende Veröffentlichung von `latest`-
Containern für jeden Feature-Branch; keine Zusammenführung oder Installation.

8 Board-Backendtests, Integrationsregression und 200 Frontendtests bestanden;
Produktionsbuild, Ruff und Übersetzungen geprüft. Vollständige Backendsuite:
659 bestanden, 6 Fehler. Vier umgebungsabhängige Fehler mit bereinigten
Provider-Einstellungen nachgeprüft (22 bestanden); zwei Teams-Katalogfehler
identisch auf unverändertem master `ea54607` reproduziert.

Echter HTTP-MCP-Test gegen Speccify mit zwei synthetischen Git-Registern:
drei Specs, Stationen 1/1/1, Counts und Commit-Stände identisch zum Web-Board;
Spec-Details gelesen. Chat-Testmodell ruft freigegebene Tools auf. Projekt-
Mitgliedschaft, Tool-Auswahl, Offline und Registerwechsel während des Lesens
geprüft. Browserprüfung de/en × dark/light, Detail, Offline/Retry, Mobilbreite
und Tastaturfokus bestanden; alle vier Screenshots angesehen.

Einrichtung und Screenshot in `docs/web-board.md`, reproduzierbare Vorschau in
itsdcloud `docs/SPECCIFY_BOARD.md`. Site-Build einschließlich lokalem Bild und
24 Doku-Tests grün. Prototyp zur menschlichen Abnahme bereit; natürliche
Modellantwort und produktive Einrichtung bleiben offen. Generalisierung erst
nach der Abnahme gemäß D3.

## Questions

Keine.
