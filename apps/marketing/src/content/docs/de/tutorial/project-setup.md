---
title: Projekt-Setup
description: Ein leerer Ordner wird ein agent-taugliches Xcode-Projekt mit Ein-Klick-Aktionen.
sidebar:
  order: 3
---

Ziel dieses Kapitels: Aus einem leeren Ordner wird ein Projekt, das
**über Ein-Klick-Aktionen** baut, startet und testet — und an dem ein
Agent arbeiten kann, ohne zu fragen, wo etwas liegt.

## 1. Projekt generieren, nicht zusammenklicken

Das Xcode-Projekt wird mit
[xcodegen](https://github.com/yonaskolb/XcodeGen) aus einer
deklarativen `project.yml` *generiert*. Das hält die
Projektdefinition diffbar, mergebar und für den Agenten pflegbar —
niemand löst `.pbxproj`-Konflikte von Hand. 4Notices Definition
beginnt so (gekürzt):

```yaml
name: FourNotice
options:
  bundleIdPrefix: com.better-apps
  developmentLanguage: en
  deploymentTarget:
    macOS: "26.0"
    iOS: "26.0"
settings:
  base:
    CODE_SIGN_STYLE: Automatic
    SWIFT_STRICT_CONCURRENCY: complete
targets:
  FourNotice:
    type: application
    platform: macOS
    sources: [Sources/Shared, Sources/macOS, Resources]
  FourNotice-iOS:
    type: application
    platform: iOS
    sources: [Sources/Shared, Sources/iOS, Resources]
```

Zwei Plattformen, ein `Sources/Shared` — dort lebt die SwiftUI-App,
jede Plattform legt eine dünne Schicht dazu. Dann:

```sh
xcodegen generate
```

Das generierte `FourNotice.xcodeproj` wird **nicht committet** — es
ist ein Build-Artefakt von `project.yml`. Jedes Build-Skript
regeneriert es zuerst, also kann es nie veralten.

## 2. Git ab Minute eins

```sh
git init -b main
git add -A && git commit -m "Generate FourNotice project from project.yml"
gh repo create 4Notice --private --source . --push
```

Ein privates Repo ab dem ersten Tag verankert die späteren Schritte:
atomare Commits, Skill-Herkunft, CI.

## 3. In der Speccify-App öffnen

Den Ordner als Projekt in der **Speccify-App** öffnen und im
Workflow-Banner **Einrichten** klicken. Die App schreibt das
Agent-Setup: `.agent/agent.md` (den Workflow-Vertrag), die
Zeiger-Dateien `CLAUDE.md` und `AGENTS.md`, die Skills
`/ticket-next` und `/ticket-ask` und die leeren Ordner `plans/` und
`board/`. Von diesem Moment an kennt jeder in diesem Verzeichnis
gestartete Terminal-Agent die Workflow-Regeln — und die App zeigt,
was der Agent tut.

## 4. Aktionen: Build, Run, Test als Knöpfe

Wiederkehrende Kommandos werden **Aktionen** in
`.agent/actions.json`. Die echten 4Notice-Einträge (gekürzt):

```json
[
  { "name": "Build (macOS)", "command": "sh scripts/build.sh" },
  { "name": "Run (macOS)",   "command": "sh scripts/run.sh" },
  { "name": "Test (macOS)",  "command": "sh scripts/test.sh" }
]
```

Die [Speccify-App führt sie selbst aus](/de/app/actions/) (im
Projekt-Root, allowlisted für den Agenten). Dass jedes Kommando
`sh scripts/….sh` heißt, ist eine Lektion, keine Stilfrage: Aktionen
laufen als **argv ohne Shell** — `&&`, Pipes und `$(…)` in einem
Aktions-Kommando kämen als wörtliche Argumente an. Zusammengesetzte
Logik lebt in Skripten:

```sh
#!/bin/sh
# scripts/build.sh — Build the macOS app (Debug). DerivedData stays in
# ~/Library: a build folder inside this iCloud-synced directory gets
# Finder xattrs and breaks codesign.
set -eu
cd "$(dirname "$0")/.."
xcodegen generate --quiet
xcodebuild -project FourNotice.xcodeproj -scheme FourNotice \
  -configuration Debug -destination 'platform=macOS' \
  -allowProvisioningUpdates build
```

Der Kommentar über DerivedData ist die zweite echte Lektion: 4Notice
liegt auf einem iCloud-gesyncten Desktop, und ein projektinterner
`build/`-Ordner fing Finder-Extended-Attributes ein, die
**`codesign` brachen**. Build-Produkte bleiben in
`~/Library/Developer/Xcode/DerivedData`; `run.sh` fragt
`xcodebuild -showBuildSettings` nach `BUILT_PRODUCTS_DIR` und startet
die App von dort.

## Wo wir stehen

Ein Klick auf die Build- und Run-Aktion in der Speccify-App baut und
startet die App; die Test-Aktion führt die Tests aus; alles, woraus
das Setup besteht —
`project.yml`, `scripts/`, `.agent/` — ist committet und lesbar.
Zeit zu entscheiden, *was* gebaut wird:
[ein Plan und ein Board](/de/tutorial/plan-and-tickets/).
