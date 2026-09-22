---
station: Done
order: 66
created: 2026-09-22
parent: 065-fragen-lesbar-kopierbar
modules: release, marketing
---
# Release 0.8.6: Agent-Fragen lesbar und kopierbar

## Why

BO 2026-09-22 („Bitte committen, pushen und releasen"): Der Frage-Umbau aus
Spec 065 soll den Kollegen über den Updater erreichen.

## What

- Version 0.8.6 in `package.json`, `tauri.conf.json`, `Cargo.toml`, `Cargo.lock`.
- Release-Notes `releases/0-8-6.md`, Landing-Link, Doku-Seite Fragen.
- Tag `v0.8.6`, Builds, Manifest, Veröffentlichung, öffentlicher Nachweis,
  Update der lokalen App.
- Außerhalb: Screenshots (Frage-Box ist kein Demo-Motiv), Windows-/Linux-Abnahme.

## Acceptance

- Wenn der Tag gepusht ist, dann sind alle Release-Jobs grün und der Draft
  trägt 20 Assets plus `latest.json` mit den finalen Notes.
- Wenn veröffentlicht ist, dann liefert `releases/latest/download/latest.json`
  Version 0.8.6 mit vier erreichbaren URLs und `speccify.io/releases/0-8-6/` ist live.
- Wenn die lokale 0.8.5 über den Updater aktualisiert, dann läuft 0.8.6 mit
  gültiger Signatur.

## Decisions

1. 2026-09-22: Patch-Version 0.8.6; einziger Inhalt ist Spec 065.

## Tasks

- [x] Version an vier Stellen.
- [x] Release-Notes, Landing-Link, Doku (`questions.md`), `stand-und-ui`.
- [x] Prüfstand (project-checks) mit Zahlen.
- [x] Commit `chore(release): prepare Speccify 0.8.6`, Push, CI/Site grün.
  Commit `112658e`; CI 35729400272, Docs 35729400291, Deploy 35729445314 — alle
  grün im ersten Lauf; `/releases/0-8-6/` live.
- [x] Tag `v0.8.6`, Release-Text im Draft, Workflow beobachten.
- [x] Draft unabhängig prüfen, veröffentlichen, öffentlicher Nachweis.
- [x] Lokale App über den Updater aktualisieren.
- [x] Abschluss: `docs(release): record verified 0.8.6 publication`, Verification, Done.

## Verification

2026-09-22, Skill `release`:

- Prüfstand: 134 Rust-Tests (3 ignored), fmt, typecheck, Python 287 passed, ruff,
  `speccify verify` ok, Marketing-Build mit `/releases/0-8-6/`; Browser-Suiten
  auf dem ausgelieferten Frontend (`14e5806`): `test_spec_questions`,
  `test_spec_navigation`, `test_team_signals`, `test_spec_modules`.
- Commit `112658e`; CI 35729400272, Docs 35729400291, Deploy 35729445314 grün
  im ersten Lauf; Release-Seite 200.
- Tag `v0.8.6`; Release-Lauf 35729920342: alle sechs Jobs grün im ersten Lauf.
- Draft (id 393741746): 20 Assets, alle hochgeladen; Notes gesetzt;
  `build_update_manifest.py` lokal: vier Plattformen verifiziert, Manifest
  identisch zum angehängten (ohne `pub_date`), URLs auf dem Tag-Pfad,
  `tauri.conf.json` gleich dem Tag.
- macOS: `codesign --verify --deep --strict` App und Binaries ok, `stapler
  validate` App und DMG ok, `spctl` App und DMG „Notarized Developer ID“, Version 0.8.6.
- Veröffentlicht per CLI; `releases/latest/download/latest.json` identisch zum
  geprüften Manifest; vier Update-URLs 200; Landing-Link auf 0.8.6.
- Update auf diesem Mac: 0.8.5-Bundle, `active_work` 0, `update_check` →
  `update_download` (30.650.645 Bytes) → `update_install`; danach `/health`
  0.8.6, `update_snapshot` `current`, dieselben vier Fenster, `codesign` ok,
  notarisiert.
- Nicht geprüft: Installation unter Windows und Linux; Sichtprüfung der
  Frage-Box an einer echten Frage (BO, Spec 008 im anderen Projekt).

## Questions
