---
station: Doing
created: 2026-09-10
order: 0
needs_human: true
ready: true
---
# Speccify mit Projektaktionen live vorführen

## Why

Im bereits geöffneten Speccify-Projekt sollen Kollegen sofort Aktionen und
einen Testknopf in der Toolbar sehen. Aktuelle Demo nicht durch Neustart unterbrechen.

## What

Fünf bestätigte lokale Aktionen: Schnelltests, Desktop-Tests, Typecheck,
Git-Überblick und echte SHA-256-Messreihe als Diagramm-Demo. Tests in die
Standard-Toolbar aufnehmen. Bestehendes Action-Format verwenden, kein App-Umbau.

## Acceptance

- Gültige actions.json enthält fünf direkt nutzbare lokale Aktionen, Tests mit toolbar=true.
- Schnelltests und Typecheck funktionieren mit der vorbereiteten Repo-Umgebung.
- Diagramm-Ausgabe entspricht dem vorhandenen Chart-Vertrag und zeigt echte Messwerte.
- Keine Aktion startet die App neu oder verändert den Git-Index/Remote-Stand.
- Laufende App bleibt für die Vorführung offen; Sichtprüfung durch Nutzer separat.

## Decisions

- D1, 2026-09-10: Nutzer fordert nutzbare Aktionen ausdrücklich an; confirmed=true,
  source=bo. Keine zusätzliche permanente Exec-Allowlist eingerichtet.
- D2: Bestehender Dateiwatcher lädt actions.json nach. Eine individuell gespeicherte
  Toolbar kann den Default übersteuern; dann Tests in Einstellungen → Toolbar aktivieren.
- D3: Generell sind Neustarts nun ausdrücklich erlaubt und erwünscht, aber mit
  anschließendem Wiederstart. Für die aktuelle Vorführung vorerst nicht neu starten.
- D4: Die Demo-Aktionen verwenden die lokale macOS-/Unix-venv; kein Windows-Setupversprechen.

## Tasks

- [x] Aktionen und kleinen ausführbaren Einstieg anlegen.
- [x] Schnelltests, Typecheck und Diagrammformat prüfen.
- [x] Neustartvereinbarung und Bestandsbuch aktualisieren.

## Verification

- Speccify-Skill: Suche nach actions ohne Treffer; bestehendes Action-Schema,
  Watcher und Toolbar-Default im Code geprüft. Kein zusätzlicher Skill importiert.
- App vor Änderung: PID 37974 auf 18768, ohne Vite.
- Alle fünf Kommandos direkt über den Action-Einstieg geprüft: Schnelltests
  7 bestanden; Desktop-Tests 61 bestanden/1 ignoriert; Typecheck und Git-Status
  Exit 0. Diagramm-Demo: 6 gültige Chart-Nachrichten mit positiven gemessenen
  Werten, letzte Serie enthält 6 Punkte. Ruff/Format und git diff --check grün.
- actions.json ist gültig, 5 bestätigte Einträge, Tests mit toolbar=true.
  Keine permanente Exec-Allowlist geändert. Direkte Ausführung geprüft, nicht
  mit einem Klick durch die native Oberfläche; Sichtabnahme bleibt offen.
- 2026-09-10 13:07 UTC: dieselbe App-PID 37974 auf 18768; kein Neustart.

## Questions

- Sichtabnahme: Sind die Aktionen und der Tests-Knopf im geöffneten Projekt sichtbar?
