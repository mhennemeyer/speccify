---
station: Done
order: 64
created: 2026-09-22
parent: 063-module-je-spec
modules: release, marketing
---
# Release 0.8.5: Module je Spec

## Why

BO 2026-09-22: Die Modul-Funktion aus Spec 063 soll dem Kollegen, der mit der
aktuellen App arbeitet, sofort zur Verfügung stehen — als reguläres Release über
den Updater, nicht als lokaler Build.

## What

- Version 0.8.5 in `package.json`, `tauri.conf.json`, `Cargo.toml`, `Cargo.lock`.
- Release-Notes `releases/0-8-5.md`, Landing-Link, Doku `specs.md`.
- Tag `v0.8.5`, vier Plattform-Builds, Manifest, Veröffentlichung, öffentlicher
  Nachweis, Update der lokalen App.
- Außerhalb: Screenshots (kein Demo-Motiv betroffen: Module erscheinen nur mit
  Frontmatter/Katalog), Windows-/Linux-Installationsabnahme, Spec 062.

## Acceptance

- Wenn der Tag gepusht ist, dann sind alle Release-Jobs grün und der Draft
  trägt 20 Assets plus `latest.json` mit den finalen Notes.
- Wenn veröffentlicht ist, dann liefert `releases/latest/download/latest.json`
  Version 0.8.5 mit vier erreichbaren URLs und `speccify.io/releases/0-8-5/` ist live.
- Wenn die lokale 0.8.4 über den Updater aktualisiert, dann läuft 0.8.5 mit
  gültiger Signatur.

## Decisions

1. 2026-09-22: Patch-Version 0.8.5 — ein Feature ohne Bruch bestehender Specs
   (Feld optional, Policy-Bump wie bei 047).

## Tasks

- [x] Version an vier Stellen.
- [x] Release-Notes, Landing-Link, Doku.
- [x] Prüfstand (project-checks) mit Zahlen.
- [x] Commit `chore(release): prepare Speccify 0.8.5`, Push, CI/Site grün.
  Commit `2b91491`. Erster Lauf: Site-Deploy Kollision mit dem vorigen Deployment,
  Windows-CI Timeout in `test_terminal_preferences` (Terminal unberührt, auf
  `30463b8` grün) — beide Jobs wiederholt, beide grün; `/releases/0-8-5/` live.
- [x] Tag `v0.8.5`, Release-Text im Draft, Workflow beobachten.
  Lauf 35716394988: macOS-Job scheiterte nach „Notarizing Finished … Accepted“
  in `bundle_dmg.sh`; `gh run rerun --failed` → alle sechs Jobs grün.
- [x] Draft unabhängig prüfen (Manifest, Signaturen), veröffentlichen, öffentlicher Nachweis.
- [x] Lokale App über den Updater aktualisieren (local-app).
- [x] Abschluss: `docs(release): record verified 0.8.5 publication`, Verification, Done.
- [x] (added) Fallstricke (`bundle_dmg.sh`, CI-Wiederholungen) im Release-Skill notiert.

## Verification

2026-09-22, Skill `release`:

- Prüfstand vor dem Commit: 134 Rust-Tests (3 ignored), fmt, typecheck, Python
  287 passed, ruff, `speccify verify` ok, Marketing-Build mit `/releases/0-8-5/`,
  sieben Board-Browser-Suiten (siehe 063).
- Commit `2b91491` auf `main`; CI-Lauf 35715586380 (Windows-Timeout in
  `test_terminal_preferences`, Wiederholung grün), Docs-Site 35715586327 grün,
  Deploy 35715586291 (Kollision, Wiederholung grün); `speccify.io/releases/0-8-5/` 200.
- Tag `v0.8.5`; Release-Lauf 35716394988: macOS zunächst rot (`bundle_dmg.sh`
  nach erfolgreicher Notarisierung), nach `rerun --failed` alle sechs Jobs grün.
- Draft (id 393642927): 20 Assets wie bei 0.8.4; Notes aus dem Scratchpad gesetzt;
  `build_update_manifest.py` lokal: vier Plattformen verifiziert (minisign),
  `latest.local.json` identisch zum angehängten `latest.json` (ohne `pub_date`),
  URLs auf dem Tag-Pfad, Notes gleich; `tauri.conf.json` gleich dem Tag.
- macOS: `codesign --verify --deep --strict` App und fünf Binaries ok, `stapler
  validate` App und DMG ok, `spctl` App und DMG „Notarized Developer ID“, Version 0.8.5.
- Veröffentlicht per CLI; `releases/latest/download/latest.json` identisch zum
  geprüften Manifest; vier Update-URLs 200; Landing-Link auf 0.8.5.
- Update auf diesem Mac: App war vom BO beendet (Download verworfen), 0.8.4-Build
  mit QA-Brücke neu geöffnet, `update_check` → `update_download` (30.650.505
  Bytes, `ready`) → `update_install`; danach `/health` 0.8.5, `update_snapshot`
  `current`, dieselben vier Fenster, `codesign` ok, `spctl` notarisiert. Board im
  Projektfenster: „Module (13)“, Chips dreier Specs, Überschneidung #63/#64.
- Nicht geprüft: Installation unter Windows und Linux; Screenshots nicht
  erneuert (kein Demo-Motiv betroffen).

## Questions
