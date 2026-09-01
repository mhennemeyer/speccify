---
title: Prerequisites
description: Everything installed and configured before the first line of code — from Xcode to your Apple Developer account.
sidebar:
  order: 2
---

Set these up once; the tutorial assumes all of them from here on.

## The platform

- **A Mac** running a current macOS. One practical warning up front:
  if your Desktop/Documents are iCloud-synced, don't keep build
  output inside a synced project folder — Finder extended attributes
  on a `build/` directory can break `codesign` later. We'll keep
  build products in Xcode's DerivedData (`~/Library`), and the
  tutorial's scripts do so explicitly.
- **Xcode** (from the App Store or
  [developer.apple.com](https://developer.apple.com/xcode/)), opened
  once so it installs its components, plus the command line tools:

  ```sh
  xcode-select --install
  ```

## Version control

- **Git** — comes with the Xcode command line tools; check with
  `git --version`.
- **A GitHub account** and the **`gh` CLI**
  ([cli.github.com](https://cli.github.com)), authenticated:

  ```sh
  brew install gh
  gh auth login
  ```

  We use GitHub for the app repo and — later — for your own skills
  repo. `gh`'s credentials also give Speccify access to private
  skill sources.

## The agent: Claude Code

Install [Claude Code](https://code.claude.com) and make sure `claude`
runs in a terminal. Any agent that reads project instruction files
works with this workflow; the tutorial's transcripts use Claude Code.

## The cockpit: the Speccify app

Install **the Speccify app** (macOS or Windows). It renders the
project's board, plans, skills, and actions — everything the agent
maintains as files under `.agent/` — and runs the project's actions
itself. No account, no server; it reads your repository. It also
bundles the local MCP servers (exec, discovery) for sandboxed
third-party clients — nothing else to install.

## The skill manager: the Speccify CLI

Install the **Speccify CLI**. It manages skill *sources*, expands
skills into projects, and checks tool implementations against their
contracts. Verify it answers:

```sh
speccify --help
```

## Project generation: xcodegen

We don't click Xcode projects together; the project file is
*generated* from a declarative `project.yml`, which keeps it
diffable and lets the agent maintain it:

```sh
brew install xcodegen
```

## Shipping tools (needed from the shipping chapters on)

- **fastlane**, via Bundler so the version is pinned in the repo:

  ```sh
  brew install ruby   # or use system ruby ≥ 3
  gem install bundler
  ```

  The project's `Gemfile` will pin fastlane; `bundle install` does
  the rest when we get there.
- **An Apple Developer Program membership**
  ([developer.apple.com/programs](https://developer.apple.com/programs/),
  99 USD/year) — required for signing, TestFlight, and the App
  Store. Registration can take a day; start it early so it's ready
  by the time the shipping chapters need it.

## Checklist

```text
✓ Xcode + command line tools     ✓ git + gh (authenticated)
✓ Claude Code (`claude`)         ✓ Speccify app
✓ Speccify CLI (`speccify --help`) ✓ xcodegen
✓ ruby + bundler (for fastlane)  ✓ Apple Developer Program (pending is ok)
```

All green? [Create the project.](/tutorial/project-setup/)
