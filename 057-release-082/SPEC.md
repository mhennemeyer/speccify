---
station: Doing
order: 57
created: 2026-09-17
needs_human: false
---
# Speccify 0.8.2 veröffentlichen

## Why

Die fertig geprüften Terminal-Findings und Shift+Enter müssen als Update in der
Windows-VM sowie auf macOS und Linux verfügbar werden.

## What

Release 0.8.2 für Specs 051–056, Website/Dokumentation und signierter Update-Feed.
Keine itsdcloud-Erweiterung für 0.9.0 in diesem Änderungssatz.

## Acceptance

- Vier Plattform-Builds und vollständige Signatur-/Manifestprüfung erfolgreich.
- GitHub-Release veröffentlicht, öffentliche Downloadziele und Feed erreichbar.
- Website beschreibt die ausgelieferten Funktionen und verbleibenden Prüfgrenzen.
- Lokale App läuft nach dem Update wieder mit den ursprünglichen Fenstern.

## Decisions

1. 2026-09-17: Nutzer autorisiert „Weiter mit 0.8.2 oder releasen, wenn fertig“.
   Implementierung und CI von 8944f7c sind grün; Release vorbereiten und publizieren.
2. 2026-09-17: Native Windows-/Linux-Systemzustellung bleibt eine benannte
   Praxiserprobung, kein behaupteter Nachweis durch CI. Keine erneute Freigabe nötig.
3. 2026-09-17: Specs 051–056 bleiben zur menschlichen Sichtabnahme ready;
   Release-Freigabe wird nicht als nachträgliche Sichtabnahme umgedeutet.

## Tasks

- [x] Quellstand, CI und Release-Freigabe prüfen.
- [x] Version, Release-Notizen, Doku und Screenshot-Drift prüfen.
- [ ] Release-Tag bauen; Installer und Signaturen prüfen.
- [ ] Veröffentlichen, Feed/Website und lokales Update prüfen.

## Verification

8944f7c: CI 35124493388, Website 35124493358, Docs 35124493241 erfolgreich.
Lokale App PID 44686, vier ursprüngliche Fenster, keine Entwürfe/Terminals.

Version 0.8.2 in allen vier Metadatenstellen konsistent. Rust 134 bestanden/3
ignoriert; Python 287 bestanden/1 deselected (mit lokalen Testservern außerhalb
der Sandbox), TypeScript, Cargo fmt, Ruff lint/format grün. Marketing-Build grün.
Zehn Demo-Bilder visuell geprüft; fünf veraltete Bilder ersetzt, Wiederholung
bestätigt stabile Motive. Playbook-Selektor an sichtbaren Aktiv-Status angepasst.

Commit/Tag: `6122c53`, `v0.8.2`; Release-Workflow `35191540790` gestartet.
CI `35191538547` vollständig erfolgreich, einschließlich Windows und Linux.
Website `35191538572` und Docs `35191538558` erfolgreich; öffentliche
Release-Notizen und Terminal-Hilfe auf speccify.io direkt geprüft.
Responsiver Website-Test (1440/390/320 px, Tastatur, ohne JavaScript) grün.

## Questions

Keine.
