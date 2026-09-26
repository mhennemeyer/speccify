---
station: Doing
order: 72
created: 2026-09-26
modules: release, marketing
---
# Release 0.8.7: Terminals überleben Neustarts, Kopieren, Dock in voller Breite

## Why

BO 2026-09-26 („Bau bitte nochmal mit dem aktuellen Stand ein Release“): der
Terminal-Stand aus den Specs 068–070 soll die Kollegen über den Updater
erreichen, bevor der Umzug (071) beginnt.

## What

- Version 0.8.7 in `package.json`, `tauri.conf.json`, `Cargo.toml`, `Cargo.lock`.
- Inhalt: Spec 068 (Kopieren aus dem Terminal), 069 (Terminal unten in voller
  Breite), 070 (Terminals überleben App-Neustarts, opt-in; Fensterzustand
  entprellt gesichert) mit den Nachbesserungen vom 2026-09-26, Spec 067
  (Skill `gitlab-deploy-key`, kein App-Code), Website auf Netlify (071, Brücke).
- Release-Notes `releases/0-8-7.md`, Landing-Link, Doku-Seite Terminal-
  Einstellungen, `website.md`.
- Tag `v0.8.7`, Builds, Manifest, Veröffentlichung, öffentlicher Nachweis,
  Update der lokalen App.
- Außerhalb: die itsdcloud-Integration (034/035 unverändert), Screenshots (kein
  Demo-Motiv betroffen), Windows-/Linux-Abnahme, Updater-Endpunkt bleibt noch
  auf GitHub (Umstellung mit dem Releases-Repo in 071).

## Acceptance

- Wenn der Tag gepusht ist, dann sind alle Release-Jobs grün und der Draft
  trägt 20 Assets plus `latest.json` mit den finalen Notes.
- Wenn veröffentlicht ist, dann liefert `releases/latest/download/latest.json`
  Version 0.8.7 mit vier erreichbaren URLs und `speccify.io/releases/0-8-7/`
  ist live (Netlify und, bis zur DNS-Umstellung, GitHub Pages).
- Wenn die lokale 0.8.6 über den Updater aktualisiert, dann läuft 0.8.7 mit
  gültiger Signatur.

## Decisions

1. 2026-09-26: Patch-Version 0.8.7; Inhalt sind die Terminal-Specs 068–070 und
   der Skill 067. Der PTY-Host ist ein neuer Sidecar (`speccify-pty-host`),
   deshalb muss der Release-Workflow ihn wie die MCPs bündeln.

## Tasks

- [x] Version an vier Stellen.
- [ ] Release-Notes, Landing-Link, Doku (`terminal-settings.md`), `website.md`.
- [ ] CI-Stand klären: CI ist seit `5e94258` rot; Ursache beheben, bevor der
      Release-Commit entsteht.
- [ ] Prüfstand (project-checks) mit Zahlen.
- [ ] Commit `chore(release): prepare Speccify 0.8.7`, Push, CI/Site grün.
- [ ] Tag `v0.8.7`, Release-Text im Draft, Workflow beobachten.
- [ ] Draft unabhängig prüfen, veröffentlichen, öffentlicher Nachweis.
- [ ] Lokale App über den Updater aktualisieren.
- [ ] Abschluss: `docs(release): record verified 0.8.7 publication`, Verification, Done.

## Verification

Noch nichts geprüft.

## Questions

Keine.
