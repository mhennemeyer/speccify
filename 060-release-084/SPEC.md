---
station: Doing
order: 60
created: 2026-09-17
needs_human: false
---
# Speccify 0.8.4: „Alles stoppen“ im Update-Dialog, Release

## Why

BO-Befund 2026-09-17: Die Meldung „Terminals oder Aktionen laufen noch“ blieb,
obwohl der Agent im Terminal beendet war. Ursache: Jede offene Terminal-Sitzung
zählt als laufende Arbeit — auch die bloße Shell nach dem Agent-Ende, und sogar
eine von selbst beendete Shell, solange ihr Panel offen war. Der Dialog nannte
keinen Ausweg. Zusätzlich soll der Fix aus Spec 059 ausgeliefert werden.

## What

- Fehlermeldung nennt die Zahl und erklärt, dass offene Terminals zählen.
- CTA **Alles stoppen** an der Meldung: beendet nach zweitem, bestätigendem Klick
  alle Terminals, laufenden Aktionen und überwachten Prozesse; installiert nichts.
- Von selbst beendete Shells zählen nicht mehr als laufende Arbeit.
- Release 0.8.4 inklusive 059 (erneute Suche nach fertigem Download).
- Außerhalb: Editor-/Entwurfsblocker automatisch auflösen (Datenverlust);
  0.9.0/itsdcloud; Windows-/Linux-Praxisabnahme.

## Acceptance

- Wenn die Installation an laufender Arbeit scheitert, dann steht „Alles stoppen“
  sichtbar an der Meldung; erst der zweite Klick beendet, danach ist die Meldung
  weg und die Installation möglich.
- Wenn eine Shell mit `exit` endet, dann blockiert sie kein Update mehr.
- Wenn `v0.8.4` gebaut ist, dann sind alle Jobs grün, Release und Feed öffentlich.

## Decisions

1. 2026-09-17: Nutzer autorisiert im Chat „mit in 0.8.4 und dann schon
   veröffentlichen“ — Zuruf für den Tag.
2. 2026-09-17: Zwei Klicks statt einem: Der Knopf bricht laufende Agenten und
   Befehle ab. Agent-Sitzungen bleiben fortsetzbar, Befehlsausgaben nicht.
3. 2026-09-17: „Alles stoppen“ installiert nicht selbst; Editor-/Entwurfsblocker
   können weiter bestehen und bleiben eine bewusste Nutzerhandlung.

## Tasks

- [x] Ursache belegen; `stop_all`/`active_work`/`update_stop_all`, beendete Shells vergessen.
- [x] Dialog-CTA mit Bestätigung; Fixture, Browser-Regression, Rust-Test.
- [ ] Version, Release-Notizen, Doku, Playbooks; volle Prüfläufe.
- [ ] Commit/Push, CI grün, Tag, Release-Workflow und Paketprüfung.
- [ ] Veröffentlichen, Feed/Website prüfen, lokale App aktualisieren, nativ prüfen.

## Verification

## Questions

Keine.
