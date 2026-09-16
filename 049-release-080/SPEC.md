---
station: Doing
order: 49
needs_human: false
---

# Release 0.8.0 für das Windows-Update

## Why

Der Nutzer möchte den Mermaid-Fix in der Windows-VM installieren und beauftragt
ausdrücklich ein Release. Zusätzlich fragt er nach dem Stand des Tauri-Updaters.

## What

Den geprüften Hauptbranch als 0.8.0 für alle bestehenden Release-Plattformen
ausliefern, Release-Notizen und Website nachführen, öffentliche Downloads prüfen.
Updater-Bestand erklären; keine ungeprüfte automatische Update-Kette aktivieren.

## Acceptance

- Windows-x64-Installer mit Mermaid-Fix öffentlich ladbar, Version 0.8.0 eindeutig.
- Release-Artefakte für alle bisherigen Plattformen vorhanden und Build-Läufe grün.
- Website und Release-Notizen nennen den Stand und manuelle Aktualisierung.
- Updater-Bestand und offene Arbeiten sind anhand von Code und Konfiguration belegt.
- Nutzeridentität für Commit/Tag, keine Attributionstrailer, lokale App offen.

## Decisions

1. 2026-09-16: Expliziter Release-Auftrag erlaubt Tag und Veröffentlichung;
   bestehender Draft-Schritt dient der Prüfung vor Veröffentlichung.
2. 2026-09-16: 0.8.0 statt Patch-Release, da neben 048 auch die fertigen
   Multi-Projekt-Funktionen und Draft-Playbooks seit 0.7 enthalten sind.
3. 2026-09-16: Updater noch nicht aktiviert: kein privater Signaturschlüssel
   oder öffentlicher Prüfkey in GitHub konfiguriert, Windows-Workflow ohne
   Update-Artefakt-/Signatur-Schritte. Grundgerüst in App vorhanden.

## Tasks

- [x] Versionen, Release-Notizen und Website nachführen und prüfen.
- [ ] Release-Commit und Tag pushen; Plattform-Builds prüfen.
- [ ] Artefakte prüfen, Release veröffentlichen, öffentliche Downloads nachweisen.
- [ ] Updater-Stand dokumentieren, lokale App erhalten, Register abschließen.

## Verification

Vorbereitung: kompletter CI-Lauf `35066449760` zum Mermaid-Fix erfolgreich,
einschließlich Windows-Rendering-Regression. Lokale App PID 68087 offen.
GitHub-Konfiguration nur anhand der Namen geprüft: Apple-Signing vorhanden,
keine Tauri-Updater-Schlüssel konfiguriert.

Release-Vorbereitung: Frontend-Build, Marketing-Build (103 Seiten), Doku-Sync,
`git diff --check` und Website-Regression für 1440/390/320 px erfolgreich.
Commit `a9da2b942b01549631bbf5c4d98054188ca4de4e` und annotierter Tag `v0.8.0`
gepusht. Release-Lauf `35071964938`, CI `35071959184`, Website `35071959200`.
Release-Notizen referenzieren Register-Snapshot
`218fbc030b630d0dbe21761b09268261803e0a48` (Implementierungsstand vor Release-Arbeit).

CI `35071959184` vollständig grün (einschließlich Windows und Linux),
Website-Deploy `35071959200` grün. Öffentliche Release-Seite `/releases/0-8-0/`
liefert 0.8.0, Mermaid-Hinweis und den Hinweis auf manuelle Updates.
Lokaler signierter App-Build 0.8.0, PID 32807: dieselben vier Fenster,
keine laufenden Terminals/Entwürfe verloren. Signaturprüfung und echte native
Mermaid-Prüfung im Programm-Playbook erfolgreich, Kundendatei unverändert.
Temporären Website-Vorschauserver beendet; gebündelte App bleibt offen.

## Questions

Keine für das beauftragte Release.
