---
station: Doing
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

- [ ] Version an vier Stellen.
- [ ] Release-Notes, Landing-Link, Doku.
- [ ] Prüfstand (project-checks) mit Zahlen.
- [ ] Commit `chore(release): prepare Speccify 0.8.6`, Push, CI/Site grün.
- [ ] Tag `v0.8.6`, Release-Text im Draft, Workflow beobachten.
- [ ] Draft unabhängig prüfen, veröffentlichen, öffentlicher Nachweis.
- [ ] Lokale App über den Updater aktualisieren.
- [ ] Abschluss: `docs(release): record verified 0.8.6 publication`, Verification, Done.

## Verification

Noch nichts ausgeführt.

## Questions
