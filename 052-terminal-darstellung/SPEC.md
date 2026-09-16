---
station: Doing
order: 52
created: 2026-09-16
needs_human: true
ready: false
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

- [ ] Native Preferences und Grenzen.
- [ ] Live-Thema, Schriftsteuerung und Größenanpassung.
- [ ] Browser-/Native-Prüfung und Dokumentation.

## Verification

Noch ausstehend.

## Questions

Keine.
