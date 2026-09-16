---
station: Doing
order: 52
created: 2026-09-16
needs_human: true
ready: true
parent: 051-terminal-findings-08
---
# Terminalfarben und Schriftgröße

## Why

Im hellen Erscheinungsbild bleibt das Terminal dunkel; die feste Schriftgröße
ist nicht an Bildschirm und Sehgewohnheiten anpassbar.

## What

Passende vollständige ANSI-Paletten für Hell/Dunkel, live dem App-Thema folgen.
Schriftgröße 8–32 px einstellbar und fensterübergreifend dauerhaft gespeichert.

## Acceptance

- Wechsel Hell/Dunkel/System passt Hintergrund, Text, Cursor und ANSI-Farben an.
- Größenwechsel verändert ein laufendes Terminal ohne Neustart oder Textverlust.
- Andere Fenster und neue Starts verwenden die gespeicherte Größe; ungültige
  Werte werden abgewiesen. PTY-Größe wird an die neue Darstellung angepasst.

## Decisions

1. 2026-09-16: Standard 14 px; direkter Zugriff im Terminal und in Einstellungen.

## Tasks

- [x] Native Preferences und Grenzen.
- [x] Live-Thema, Schriftsteuerung und Größenanpassung.
- [x] Browser-/Native-Prüfung und Dokumentation.

## Verification

`test_terminal_preferences.mjs` und nativer Preferences-Test grün. `test_terminal_settings_app.py` im finalen gebündelten Build grün: Light/Dark, globaler Größenwechsel in zwei Fenstern, kleinerer PTY-Spaltenwert, erhaltener Unicode-Text und Shell-Variable nach Änderung. Wiederanlauf nutzt gespeicherte Größe. Terminalrahmen und Bedienelemente folgen ebenfalls dem Theme. Dokumentiert in der neuen Bedienhilfe.

## Questions

Keine.
