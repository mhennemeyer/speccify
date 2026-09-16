---
station: Doing
order: 55
created: 2026-09-16
needs_human: true
ready: false
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
- [ ] Harmloser praktischer Test und Research-Ergebnis.

## Verification

Noch ausstehend.

## Questions

Keine.
