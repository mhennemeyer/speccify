---
station: Doing
order: 53
created: 2026-09-16
needs_human: true
ready: true
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

- [x] Host-Signale und bestehende Popup-/Notification-Wege prüfen.
- [x] Meldungen, Einstellungen und Fokussierung implementieren.
- [x] Rückfragen-/Redraw-/Mehrfenster-Regressionen prüfen.

## Verification

Browser-Suite grün: fragmentierte ANSI-Ausgabe, bekannte englische/deutsche Freigabefrage, verborgenes Terminal, OSC 9, Deduplizierung, neue Meldung nach Benutzereingabe, deaktivierte Optionen und Löschen bei Prozessende. Native OSC-Meldung aus echtem PTY in genau einem von zwei Fenstern, Portal außerhalb versteckter Fläche und Sprung zum Terminal grün. Test-Systemmeldung unter macOS ohne API-Fehler gesendet; tatsächliche OS-Anzeige kann durch Systemeinstellungen unterdrückt werden. Windows/Linux nicht nativ geprüft. Keine automatischen Antworten oder Freigaben. Bedienhilfe erklärt Grenzen und OS-Test.

## Questions

Keine.
