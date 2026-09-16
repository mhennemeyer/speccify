---
station: Doing
order: 56
created: 2026-09-16
needs_human: true
ready: false
parent: 051-terminal-findings-08
---
# Shift+Enter im Agent-Terminal

## Why

Shift+Enter wird wie Enter gesendet und erzeugt deshalb keinen Zeilenumbruch
im Agent-Eingabefeld; ein unfertiger Auftrag kann ungewollt abgeschickt werden.

## What

Shift+Enter vom normalen Enter unterscheidbar an den PTY-Host übertragen.
Eingabeverhalten in Codex und Claude prüfen; keine globale Host-Konfiguration ändern.

## Acceptance

- Shift+Enter sendet genau ein modifiziertes Tastenereignis, kein normales CR.
- Codex/Claude können einen mehrzeiligen Entwurf schreiben, ohne ihn abzusenden.
- Enter, Alt+Enter, Ctrl-C und Clipboard-Verhalten bleiben erhalten.
- Laufende Sitzung und Eingabetext bleiben bei der Eingabe bestehen.

## Decisions

1. 2026-09-16: Nutzer-Finding für 0.8.x. xterm 5.5 ignoriert Shift im
   Enter-Zweig. CSI-u `ESC[13;2u` hält die Taste unterscheidbar; kein LF/CR als
   Ersatz, das Shells oder Hosts als Absenden interpretieren könnten.
2. 2026-09-16: IME-Komposition und Kombinationen mit weiteren Modifikatoren
   verbleiben beim normalen Terminal-Handler. Keine pauschale Kitty-Unterstützung
   ankündigen; hier wird genau eine fehlende Tastenkombination ergänzt.

## Tasks

- [x] Ursache und Host-Verarbeitung prüfen.
- [x] Shift+Enter-Zustellung und Browser-Regression ergänzen.
- [ ] Echte Host-Eingabe, Build, Doku und lokale App prüfen.

## Verification

Quellcode: `@xterm/xterm/src/common/input/Keyboard.ts`, Enter sendet CR und
wertet nur Alt aus. Installiert: Codex 0.154.0, Claude 2.1.273.

## Questions

Keine.
