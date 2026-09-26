---
station: Doing
order: 69
created: 2026-09-25
needs_human: true
ready: true
parent: 051-terminal-findings-08
---
# Terminal unten in voller Fensterbreite

## Why

Das unten angedockte Agent-Terminal lag nur unter der Inhaltsspalte; Navigator
und Inspektor reichten bis zum Fensterboden. Zeilen des Agenten wurden dadurch
unnötig umgebrochen, und die Fläche neben dem Terminal blieb ungenutzt
(Nutzerwunsch 2026-09-25).

## What

Im Projekt- und im Workspace-Fenster liegt die Bottom-Bar (Griff und Terminal)
über alle Rasterspalten, unter Navigator, Inhalt und rechter Seitenleiste; die
Spalten enden über ihr. Das rechte Dock bleibt unverändert. Breiten, Höhe und
Sichtbarkeiten werden weiter pro Projekt gemerkt.

Nicht enthalten: Terminal im Dashboard-Fenster, neue Dock-Positionen.

## Acceptance

- Wenn das Terminal unten angedockt und sichtbar ist, dann beginnt es am linken
  Fensterrand und endet am rechten, unabhängig von Navigator und Inspektor.
- Wenn Navigator oder Inspektor sichtbar sind, dann enden sie oberhalb des
  Terminals; der Höhen-Griff läuft über die ganze Breite.
- Wenn das Terminal rechts angedockt ist, dann ist das Layout wie zuvor.
- Bestehende Layout-Einstellungen bleiben gültig; keine Migration nötig.

## Decisions

1. 2026-09-25: Reine Rasterplatzierung (Grid-Zellen), kein neues Layout-Feld;
   die Spalten enden in Zeile 4, Griff und Terminal nehmen `1 / -1`.

## Tasks

- [x] Rasterzellen in ProjectShell und WorkspaceShell umstellen.
- [x] Browser-Regression für die Geometrie ergänzen; Doku und Playbook nachziehen.
- [x] Lokale App neu bauen und im echten Fenster prüfen.

## Verification

2026-09-25, lokaler Debug-Build 0.8.6, Developer-ID-signiert:

- `pnpm --filter speccify-desktop typecheck` bestanden.
- `node scripts/test_action_output.mjs` (Projektfenster, Dock unten und rechts)
  bestanden, neu: Terminal unten beginnt bei x=0, endet am Fensterrand,
  Navigator und Inhalt enden darüber.
- `node scripts/test_workspace_layout.mjs` bestanden, neu: Dock rechts liegt
  neben dem Navigator, nach dem Umdocken nach unten volle Breite; der PTY
  überlebt das Umdocken weiterhin.
- `node scripts/test_terminal_preferences.mjs` bestanden.
- Gebündelte App über die QA-Brücke gemessen: Projektfenster iKanban
  1258 px breit, Terminal von 0 bis 1258, Oberkante 373, Navigator/Inhalt/
  Inspektor enden bei 368. Workspace-Fenster war rechts angedockt und
  unverändert; das untere Dock des Workspace-Fensters ist im Mock geprüft.
- Offen: menschliche Sichtabnahme.

## Questions

Keine.
