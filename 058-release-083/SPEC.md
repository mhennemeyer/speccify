---
station: Done
order: 58
created: 2026-09-17
needs_human: false
---
# Speccify 0.8.3 veröffentlichen und Abläufe als Skills festhalten

## Why

Schlägt „Installieren und neu starten“ fehl, stand die Fehlermeldung unter dem
Knopf im scrollenden Update-Dialog und war bei langen Release-Notizen oder
kleinem Fenster nicht sichtbar. Der Fix (`01beefa`) soll als Update ankommen.
Außerdem existieren wiederkehrende Abläufe (Release, Prüfstand, lokale App
aktualisieren) bisher nur verstreut in `docs/release.md`, Playbooks und
früheren Release-Specs.

## What

- Release 0.8.3 mit dem Update-Dialog-Fix; Website-Notizen, signierter Feed.
- Wiederkehrende Abläufe als Projekt-Skills unter `.agent/skills/`.
- Außerhalb: neue Funktionen, 0.9.0/itsdcloud, Windows-/Linux-Praxisabnahme.

## Acceptance

- Wenn die Installation blockiert wird, dann ist die Fehlermeldung ohne
  Scrollen im Dialog sichtbar (Browserprüfung bei kleinem Fenster).
- Wenn der Tag `v0.8.3` gebaut ist, dann sind alle vier Plattform-Jobs und die
  Manifest-Prüfung grün, das Release veröffentlicht und `latest.json` öffentlich.
- Wenn ein Agent „Release erstellen“ o. Ä. hört, dann findet er unter
  `.agent/skills/` einen vollständigen, geprüften Ablauf.

## Decisions

1. 2026-09-17: Nutzer autorisiert im Chat „als 0.8.3 veröffentlichen“ — das ist
   der Zuruf für den Tag.
2. 2026-09-17: Skills verweisen auf `docs/release.md` für Einrichtung und
   Hintergründe, statt es zu duplizieren; der Skill hält den Ablauf und die
   in 049–057 gelernten Fallstricke.

## Tasks

- [x] Fix Update-Dialog (`01beefa`), Typecheck und Browserprüfung.
- [x] Version, Release-Notizen, Playbooks; volle Prüfläufe.
- [x] Commit/Push, CI grün, Tag, Release-Workflow und Paketprüfung.
- [x] Veröffentlichen, Feed/Website prüfen, lokale App aktualisieren.
- [x] Abläufe als Skills anlegen und gegen diesen Release-Lauf prüfen.

## Verification

Fix `01beefa`: Browserprüfung 900×420, 30 Zeilen Notizen, blockierte Installation;
Meldung vollständig im sichtbaren Bereich. Neue Regression in
`scripts/test_updates.mjs` schlägt mit altem Layout fehl (Meldung bei y=702 außerhalb
des 357 px hohen Dialogs) und besteht mit dem neuen.

Vorbereitung `c79d769`: Version 0.8.3 an vier Stellen. Rust 134 bestanden/3
ignoriert; Python 287 bestanden; TypeScript, Cargo fmt, Ruff lint/format grün;
Update-UI-Regression in Chrome; Marketing-Build 111 Seiten; `speccify verify` ok.
CI 35207850448 vollständig grün inkl. Windows/Linux; Docs 35207850453 grün;
Deploy site 35207850454 zunächst „in progress deployment“ (Kollision mit dem
vorherigen Push), nur fehlgeschlagenen Job wiederholt, danach grün;
https://speccify.io/releases/0-8-3/ direkt abgerufen.

Tag `v0.8.3` auf `c79d769`; Release-Workflow 35208539760: alle sechs Jobs im
ersten Lauf erfolgreich. Endgültiger Release-Text vor dem Manifest-Job gesetzt.
Unabhängige Prüfung: 20 Assets; vier Update-Pakete samt Signaturen geladen und
das Manifest lokal mit `build_update_manifest.py` neu erzeugt (Größe, SHA-256,
minisign) – identisch zum angehängten `latest.json`, Notizen identisch zum
Release-Text. macOS: App und fünf Binaries unter Contents/MacOS bestehen codesign;
App und DMG gestapelt, Gatekeeper „Notarized Developer ID“.

Veröffentlicht 2026-09-17T10:27:30Z:
https://github.com/mhennemeyer/speccify/releases/tag/v0.8.3. Öffentliches
latest.json byte-identisch zum geprüften; vier Ziel-URLs HTTP 200 ohne Anmeldung.

Echter Upgrade-Nachweis: lokale veröffentlichte 0.8.2 (PID 25222, vier Fenster,
keine Blocker) über die QA-Brücke mit den echten Updater-Befehlen: 0.8.3
gefunden, 30.614.837 Bytes signaturgeprüft geladen, installiert; Neustart
PID 25335, Version 0.8.3, Zustand `current`, dieselben vier Fenster, installierte
Signatur gültig. Dialogstruktur (fester Rahmen, ein Scrollbereich) in der
installierten App per DOM-Prüfung bestätigt; Dialog wieder geschlossen.

Skills `release`, `project-checks`, `local-app`, `ui-browser-check`,
`website-publish` angelegt; der Release-Skill wurde parallel zu diesem Lauf
geschrieben und an ihm korrigiert (Manifest-Nachbau, Deploy-Kollision,
venv-Fallstrick). `agent.md` verweist darauf.

Nicht nachgewiesen: Installation/Update unter Windows und Linux; Sichtprüfung des
Fehlerfalls in der nativen App durch einen Menschen (blockierte Installation
wurde nativ nicht provoziert, um keine Arbeit zu gefährden).

## Questions

Keine.
