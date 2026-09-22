---
station: Doing
order: 64
created: 2026-09-22
parent: 063-module-je-spec
modules: release, docs
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
- [ ] Prüfstand (project-checks) mit Zahlen.
- [ ] Commit `chore(release): prepare Speccify 0.8.5`, Push, CI/Site grün.
- [ ] Tag `v0.8.5`, Release-Text im Draft, Workflow beobachten.
- [ ] Draft unabhängig prüfen (Manifest, Signaturen), veröffentlichen, öffentlicher Nachweis.
- [ ] Lokale App über den Updater aktualisieren (local-app).
- [ ] Abschluss: `docs(release): record verified 0.8.5 publication`, Verification, Done.

## Verification

Noch nichts ausgeführt.

## Questions
