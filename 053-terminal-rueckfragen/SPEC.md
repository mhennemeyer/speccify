---
station: Backlog
order: 53
created: 2026-09-16
needs_human: true
ready: false
parent: 051-terminal-findings-08
---
# Rückfragen aus dem Terminal sichtbar machen

## Why

Berechtigungsfragen werden besonders auf Windows übersehen und halten Arbeit an.

## What

Terminal-Signale und vorsichtige Erkennung sichtbarer Rückfragen lösen eine
App-Meldung mit Sprung zum betroffenen Terminal sowie optionale OS-Notifications
aus. Meldungen gruppieren/entprellen; keine automatische Freigabe von Befehlen.

## Acceptance

- Eine Berechtigungsfrage wird auch bei verborgenem Terminal sichtbar.
- Die Meldung führt zum richtigen Fenster/Terminal, ohne eine Antwort zu senden.
- Wiederholtes Neuzeichnen desselben Prompts erzeugt keine Meldungsflut.
- Systembenachrichtigungen können eingestellt/getestet werden; fehlende OS-
  Berechtigung verhindert nicht die Meldung innerhalb der App.

## Decisions

1. 2026-09-16: Host-Signale bevorzugen; Text-Fallback klar als Hinweis behandeln.

## Tasks

- [ ] Host-Signale und bestehende Popup-/Notification-Wege prüfen.
- [ ] Meldungen, Einstellungen und Fokussierung implementieren.
- [ ] Rückfragen-/Redraw-/Mehrfenster-Regressionen prüfen.

## Verification

Noch ausstehend.

## Questions

Keine.
