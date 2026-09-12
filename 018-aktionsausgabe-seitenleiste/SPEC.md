---
station: Doing
created: 2026-09-10
order: 0
needs_human: true
ready: true
---
# Aktionsausgaben als Tabs neben dem Inspektor

## Why

Tests lassen sich über die Toolbar starten, ihre Ausgabe ist aber nur in der
Aktionskarte sichtbar. Der Nutzer erwartet die Ausgabe sofort neben dem Inspektor.

## What

Projektweite Ausgabetabs in der rechten Seitenleiste für bestehende lokale
Projektaktionen. Bestehende Ausführung und Ereignisse weiterverwenden; keine
zweite Prozessverwaltung. Keine persistente Laufhistorie oder Git-Ausgabe-Migration.

## Acceptance

- Start über Toolbar bei geöffnetem Board zeigt automatisch rechts die Live-Ausgabe.
- Auch eine ausgeblendete Seitenleiste öffnet sich; der Haupttab bleibt unverändert.
- Verschiedene Aktionen erhalten eigene Tabs mit Status, Text/Diagrammen und Stop.
- Erneuter Klick während eines Laufs zeigt dessen Ausgabe, ohne Neustart/Verlust.
- Abgeschlossene Tabs bleiben bis zum Schließen; erneuter Lauf ersetzt die alte Ausgabe.
- Inspektor und Terminal bleiben erreichbar, auch bei unten angedocktem Terminal.
- Nach App-Neustart gibt es keinen leeren, wiederhergestellten Ausgabetab.

## Decisions

- D1, 2026-09-10: Umsetzung ausdrücklich durch Nutzer beauftragt; eine Einheit
  pro Aktion statt eines unbegrenzt anwachsenden Tabs pro Testlauf.
- D2: Letzte 2000 Ausgabeelemente wie bisher, nur im Fensterspeicher. Laufende
  Tabs erst nach Stop/Prozessende schließen. Kein implizites Stoppen beim Tabwechsel.
- D3: Beide nativen Ereignis-Listener müssen bereit sein, bevor ein Prozess startet.
- D4, 2026-09-10: Nutzer gibt den Update-Neustart ausdrücklich frei; temporäre
  Neustartsperre aufgehoben. App unmittelbar nach Bundle-Bau wieder öffnen.

## Tasks

- [x] Gemeinsame Ausgabetabs und automatische Sichtbarkeit implementieren.
- [x] Doppelstart und frühe Ausgabe vor Listener-Anmeldung absichern.
- [x] Interaktionen, Fehler, Diagramme und Layout-Wiederherstellung prüfen.
- [x] Playbooks aktualisieren und lokalen Build ohne Eingriff in laufende App prüfen.
- [x] Gebündelte lokale App nach geltender Neustartfreigabe bereitstellen und öffnen.

## Verification

- Speccify-Skill, Iteration 1: Suche nach output ohne Treffer; vorhandene
  Action-Ereignisse und Portal-Architektur wiederverwendet. Kein Skillimport nötig.
- Frontend-Typecheck nach erster Umsetzung grün.
- Iteration 1 abgeschlossen: `scripts/test_action_output.mjs` gegen isolierten
  Vite-Server auf 1421 mit installiertem Chrome/Playwright. Beide Terminal-Docks:
  Toolbar-Start bei offenem Board und ausgeblendeter Seitenleiste, sofortige
  Ausgabe bei verzögerten Listenern, Doppelstart, getrennte parallele Ausgaben,
  Diagramme, Stop/Stopfehler, Startfehler/Retry, Schließen, 2000-Elemente-Limit,
  Start aus Aktionskarte, Exit 0/1 und Reload grün. Separat: fehlgeschlagene
  Listener zeigen Fehler und starten keinen unbeobachtbaren Prozess.
- Testaufruf: `PLAYWRIGHT_CHANNEL=chrome PLAYWRIGHT_MODULE=<installiertes-playwright>/index.mjs
  node scripts/test_action_output.mjs` (Node mit Type-Stripping für Layout-Test).
  Frühe Testläufe korrigierten den Toolbar-Selektor und die nur einmal anzuwendende
  Layout-Fixture; abschließender vollständiger Lauf Exit 0, keine JS-Seitenfehler.
- Screenshot der Mock-Oberfläche visuell geprüft: Board bleibt offen, rechter
  Tests-Tab zeigt Fortschritt, Stop, Text und Diagramm; Terminal unten bleibt sichtbar.
- `pnpm --filter speccify-desktop typecheck`, Frontend-Build und `git diff --check`
  grün. `pnpm --filter speccify-desktop tauri build --debug --no-bundle --no-sign`
  grün, abschließender Build enthält die letzten Änderungen. Bestehende Warnung
  zum großen JS-Chunk; kein neuer Buildfehler. Keine Signierung/Notarisierung.
- 2026-09-10 13:32 UTC: ursprüngliche App PID 37974 auf 18768 weiter offen,
  Bundle nicht überschrieben. Testserver auf 1421 anschließend beendet. Noch
  keine Bereitstellung/Sichtabnahme im nativen Nutzerfenster.
- 2026-09-10 13:38 UTC: regulärer App-Quit nach Freigabe, anschließend
  `bash scripts/dev.sh --app --prepared --ui-port=18768` Exit 0. Neues Bundle
  geöffnet: PID 61901 auf 18768, kein Vite erforderlich. Bundle-Binary entspricht
  dem gebauten Binary (`cmp` Exit 0). Fensterprüfung bestätigt speccify, iKanban,
  AVC und Hauptfenster. Vorherige Terminal-Sitzung beim Quit unterbrochen;
  fachliche Sitzungsfortsetzung und native Sichtabnahme nicht behauptet.

## Questions

- Menschliche Sichtabnahme nach Bereitstellung der lokalen App.

### Q1 · answered · 2026-09-10T13:32:14Z

Ist die Vorführung beendet und der kurze Update-Neustart jetzt möglich?
Die generelle Neustartfreigabe gilt, aber das zuletzt ausdrücklich angeordnete
„kurz nicht neu starten“ wird bis zur Rückmeldung respektiert. Nach Freigabe
laufende Aufträge prüfen, App kurz beenden, Bundle bauen, sofort wieder öffnen
und Projektwiederaufnahme prüfen. Frage gemäß spec-ask dokumentiert.

### A1 · bo · 2026-09-10T13:38:53Z

„Dann bitte die App neu starten.“ Update-Neustart ausgeführt, App und
gespeicherte Projektfenster wieder geöffnet. Bereit für menschliche Sichtabnahme.
