---
station: Done
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
- [x] Release-Notes, Landing-Link, Doku (`terminal-settings.md`), `website.md`.
- [x] CI-Stand klären: CI war seit `5e94258` rot — der neue Sidecar
      `speccify-pty-host` fehlte in den Sidecar-Schritten der Windows-/Linux-
      Jobs (ci.yml) und im Windows-Release-Job, dazu ein Clippy-Fund im
      Host-Integrationstest. Beides im Release-Commit behoben.
- [x] Prüfstand (project-checks) mit Zahlen.
- [x] Commit `chore(release): prepare Speccify 0.8.7`, Push, CI/Site grün.
  Commit `53323c4`; CI 36233563214, Docs 36233563203, Deploy 36233563131 und
  36233565112 — alle grün im ersten Lauf; `/releases/0-8-7/` live auf
  GitHub Pages und (manueller Deploy) auf Netlify.
- [x] Tag `v0.8.7`, Release-Text im Draft (id 397180638), Workflow 36233884077
      beobachten.
- [x] Draft unabhängig prüfen, veröffentlichen, öffentlicher Nachweis.
- [x] Lokale App über den Updater aktualisieren.
- [x] Abschluss: `docs(release): record verified 0.8.7 publication`, Verification, Done.

## Verification

2026-09-26, Skill `release`:

- Prüfstand: 134 Rust-Tests Desktop (3 ignored) + 5 pty-host, `cargo fmt`,
  Clippy `--workspace --exclude speccify-desktop -D warnings`, Typecheck,
  Python 287 passed, Ruff check/format, `speccify verify` ok, Marketing-Build
  119 Seiten mit `/releases/0-8-7/`; Browser-Suiten auf diesem Frontend:
  `test_terminal_reattach`, `test_terminal_preferences`, `test_action_output`,
  `test_workspace_layout`.
- CI war seit `5e94258` rot (Sidecar `speccify-pty-host` fehlte in den
  Sidecar-Schritten der Windows-/Linux-Jobs; Clippy im Host-Test); im
  Release-Commit `53323c4` behoben. CI 36233563214, Docs 36233563203, Deploy
  36233563131/36233565112 grün im ersten Lauf; Release-Seite 200 auf GitHub
  Pages und Netlify (manueller Deploy, Token-Secret fehlt noch).
- Tag `v0.8.7`; Release-Lauf 36233884077: alle sechs Jobs grün im ersten Lauf.
- Draft (id 397180638): 20 Assets, alle hochgeladen; Notes vor dem Manifest-Job
  gesetzt; lokal nachgebautes Manifest identisch mit `latest.json` (vier
  Plattformen, Tag-URLs, Notes); App und alle sechs Binaries unter
  `Contents/MacOS` inklusive `speccify-pty-host` signiert; Stapler auf App und
  DMG gültig; `spctl` beide „Notarized Developer ID“; Bundle-Version 0.8.7.
- Veröffentlicht 10:13 UTC per CLI. Öffentliches `latest.json` gleich der
  lokalen Nachbildung, vier Ziel-URLs 200 ohne Anmeldung;
  `speccify.io/download/latest.json` (Netlify) leitet 302 dorthin; Landing-Link
  zeigt 0.8.7.
- Update 0.8.6→0.8.7 der lokalen App über den echten Updater per QA-Brücke:
  Suche → `available 0.8.7`, Download 31.185.538 Bytes → `ready`, Installation
  und Neustart; neue PID, Bundle 0.8.7, `codesign --verify --deep --strict`
  gültig, `speccify-pty-host` im Bundle, Zustand `current`, beide Fenster
  zurück, das gehostete Workspace-Terminal mit laufendem Claude wieder
  verbunden.
- Nicht geprüft: Installation und Host-Prozess unter Windows/Linux (CI baut,
  installiert nicht); menschliche Sichtabnahme der Specs 068–070 bleibt offen.

## Questions

Keine.
