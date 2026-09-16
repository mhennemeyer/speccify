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

- [ ] Versionen, Release-Notizen und Website nachführen und prüfen.
- [ ] Release-Commit und Tag pushen; Plattform-Builds prüfen.
- [ ] Artefakte prüfen, Release veröffentlichen, öffentliche Downloads nachweisen.
- [ ] Updater-Stand dokumentieren, lokale App erhalten, Register abschließen.

## Verification

Vorbereitung: kompletter CI-Lauf `35066449760` zum Mermaid-Fix erfolgreich,
einschließlich Windows-Rendering-Regression. Lokale App PID 68087 offen.
GitHub-Konfiguration nur anhand der Namen geprüft: Apple-Signing vorhanden,
keine Tauri-Updater-Schlüssel konfiguriert.

## Questions

Keine für das beauftragte Release.
