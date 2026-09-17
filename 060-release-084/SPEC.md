---
station: Done
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
- [x] Version, Release-Notizen, Doku, Playbooks; volle Prüfläufe.
- [x] Commit/Push, CI grün, Tag, Release-Workflow und Paketprüfung.
- [x] Veröffentlichen, Feed/Website prüfen, lokale App aktualisieren, nativ prüfen.

## Verification

Ursache im Code belegt: `Terminals::has_active_work` zählte jede Sitzung in der
Map; der Reader-Thread entfernte beendete Shells nicht, das tat erst das
Schließen des Panels.

Vorbereitung `765f3c3`: Rust 134 bestanden/3 ignoriert (inkl. `stop_all` auf
echtem PTY: Zähler, Claim und Kontextdatei frei, App nicht im Shutdown-Zustand);
Python 287 bestanden; TypeScript, Cargo fmt, Ruff grün; Marketing-Build 113
Seiten; `speccify verify` ok. `scripts/test_updates.mjs`: Knopf bei 900×420
sichtbar, erster Klick beendet nichts, Abbrechen, Bestätigung „2 Terminals/Aktionen
jetzt beenden“, Status „2 beendet“, Meldung weg, Installation danach möglich.
CI 35215355251, Docs 35215355207, Deploy 35215355189 grün.

Tag `v0.8.4`; Release-Workflow 35215755113: alle sechs Jobs im ersten Lauf grün.
20 Assets; Manifest lokal nachgebaut (Größe, SHA-256, minisign) und identisch,
Notizen identisch zum Release-Text. macOS: App, fünf Binaries und DMG signiert,
gestapelt, „Notarized Developer ID“. Veröffentlicht 2026-09-17T11:54:28Z:
https://github.com/mhennemeyer/speccify/releases/tag/v0.8.4. Öffentliches
latest.json byte-identisch; vier Ziel-URLs HTTP 200; Website-Seite live.

Upgrade 0.8.3→0.8.4 über die QA-Brücke mit den echten Updater-Befehlen:
30.633.148 Bytes, Neustart PID 57846, Version 0.8.4, `current`, dieselben vier
Fenster, Signatur gültig. Nativ in 0.8.4 mit Wegwerf-Shells (zuvor
`active_work: 0`, also nichts vom BO betroffen): Shell A geöffnet → 1, `exit` → 0;
Shells B und C, in B `sleep 600` → 2; `update_stop_all` → 2 beendet, 0, kein
`sleep`-Prozess mehr.

Nicht nachgewiesen: der Knopf im nativen Dialog bei tatsächlich blockierter
Installation (setzt ein neueres Update voraus; Dialog im Browser, Kommando nativ
geprüft); Windows-/Linux-Installation.

## Questions

Keine.
