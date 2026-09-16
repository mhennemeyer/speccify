---
station: Doing
order: 55
created: 2026-09-16
needs_human: true
ready: true
parent: 051-terminal-findings-08
---
# Recherche: Einfügen und Enter im Terminal

## Why

Ein expliziter Klick könnte Einfügen und Absenden verbinden, statt beide Schritte
getrennt auszuführen.

## What

PTY-Steuerzeichen, Bracketed Paste und Host-Bereitschaft mit harmlosen Testdaten
prüfen. Ergebnis als Research dokumentieren; bestehende Übergabe nicht beiläufig
auf automatisches Ausführen umstellen.

## Acceptance

- Technische Möglichkeit und Grenzen für Shell, Codex und Claude sind benannt.
- Praktischer PTY-Test unterscheidet Einfügen von Absenden.
- Vorschlag nennt bewussten Bedienknopf und Fehlerfälle statt stiller Ausführung.

## Decisions

1. 2026-09-16: Nutzer fragt ausdrücklich nach Research; Umsetzung eines neuen
   Senden-Knopfs ist eine nachfolgende Entscheidung.

## Tasks

- [x] Bestehende Schreib-/Pastepfade und Host-Verhalten prüfen.
- [x] Harmloser praktischer Test und Research-Ergebnis.

## Verification

`scripts/test_terminal_settings_app.py` im finalen gebündelten Build grün: zwei harmlose Shellzeilen per Bracketed Paste, Testdatei bleibt vor Enter absent; danach `terminal_write` mit separatem `\r`, Datei enthält genau `first-second`. Unicode, Ctrl-C und Neustart ebenfalls grün. Ergebnis und Grenzen für Codex/Claude in `docs/terminal-enter-research.md`: Transport möglich, Bereitschaft bzw. Besitz des Eingabefokus nicht zuverlässig aus dem PTY ableitbar. Kein zusätzlicher Codex-/Claude-Modellaufruf für diese Research-Prüfung. Bestehende Handover-Browserregression bestätigt weiterhin kein automatisches Enter.

## Questions

Keine.
