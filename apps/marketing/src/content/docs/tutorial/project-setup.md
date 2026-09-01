---
title: Project setup
description: An empty folder becomes an agent-ready Xcode project with one-click actions.
sidebar:
  order: 3
---

Goal of this chapter: an empty folder turns into a project that
builds, runs, and tests **from one-click actions** — and that an agent
can work on without asking where anything is.

## 1. Generate the project, don't click it

The Xcode project is *generated* from a declarative `project.yml`
with [xcodegen](https://github.com/yonaskolb/XcodeGen). That keeps
the project definition diffable, mergeable, and maintainable by the
agent — nobody resolves `.pbxproj` conflicts by hand. 4Notice's
definition starts like this (abridged):

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

Two platforms, one `Sources/Shared` — the SwiftUI app lives there,
each platform adds a thin layer. Then:

```sh
xcodegen generate
```

The generated `FourNotice.xcodeproj` is **not committed** — it is a
build artifact of `project.yml`. Every build script regenerates it
first, so it can never be stale.

## 2. Git from minute one

```sh
git init -b main
git add -A && git commit -m "Generate FourNotice project from project.yml"
gh repo create 4Notice --private --source . --push
```

A private repo from day one anchors the later steps: atomic commits,
skill provenance, CI.

## 3. Open it in the Speccify app

Open the folder as a project in **the Speccify app** and click
**Set up** in the workflow banner. The app writes the agent setup:
`.agent/agent.md` (the workflow contract), pointer files `CLAUDE.md`
and `AGENTS.md`, the `/ticket-next` and `/ticket-ask` skills, and the
empty `plans/` and `board/` folders. From this moment, any terminal
agent started in this directory knows the workflow rules — and the
app shows whatever the agent does.

## 4. Actions: build, run, test as buttons

Recurring commands become **actions** in `.agent/actions.json`. The
real 4Notice entries (abridged):

```json
[
  { "name": "Build (macOS)", "command": "sh scripts/build.sh" },
  { "name": "Run (macOS)",   "command": "sh scripts/run.sh" },
  { "name": "Test (macOS)",  "command": "sh scripts/test.sh" }
]
```

The [Speccify app runs them itself](/app/actions/) (project-rooted,
allowlisted for the agent). Note that every command is
`sh scripts/….sh` — that's a lesson, not a style choice: actions run
as **argv without a shell**, so `&&`, pipes, and `$(…)` in an action
command would arrive as literal arguments. Compound logic lives in
scripts:

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

That comment about DerivedData is the second real lesson: 4Notice
lives on an iCloud-synced Desktop, and an in-project `build/` folder
picked up Finder extended attributes that **broke `codesign`**. Build
products stay in `~/Library/Developer/Xcode/DerivedData`; `run.sh`
asks `xcodebuild -showBuildSettings` for `BUILT_PRODUCTS_DIR` and
launches the app from there.

## Where we are

One click on the Build and Run actions in the Speccify app builds
and launches the app; the Test action runs the tests; everything the
setup consists of — `project.yml`,
`scripts/`, `.agent/` — is committed and readable. Time to decide
*what* to build: [a plan and a board](/tutorial/plan-and-tickets/).
