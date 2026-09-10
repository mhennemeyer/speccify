---
title: Importing skills
description: Adding a skills source and taking a skill through expand, execute, evaluate.
sidebar:
  order: 6
---

Shipping a Mac app raises problems unrelated to the app itself:
notarization, release checks, certificates — solved before, possibly
by you in the last project. This chapter imports those solutions into
4Notice as **skills**, from a skills repo.

If the concepts are new, the [Speccify section](/speccify/overview/)
explains them; here we just do it.

## 1. Add the source

In the Speccify app's skills tab, under **Browse sources**, add the repo by URL
(or `speccify add` in the terminal). For 4Notice the source is a
private GitHub repo of skill bundles; access rides on the same `gh`
credentials git already uses. The project remembers its dependencies
in `speccify.yaml`:

```yaml
dependencies:
  git+https://github.com/<you>/<skills-repo>#skills/macos-notarize-tauri: ^1.0
  git+https://github.com/<you>/<skills-repo>#skills/release-checks: ^1.0
```

The repo URL is the identity, tags are the versions, a bundle is a
directory — `git+<url>#<path>`.

## 2. Import = expand

Importing a skill from the sources list runs the
[expand step](/speccify/expand/) and ends with a task list handed to
the agent. What actually landed in 4Notice from two requested skills:

```text
.agent/skills/macos-notarize-tauri/     ← requested
.agent/skills/apple-developer-id-cert/  ← came along: the first one `uses` it
.agent/skills/release-checks/           ← requested
.agent/tools/check-entitlements/        TOOL.md + fixtures
.agent/tools/check-plist-keys/          TOOL.md + fixtures
.agent/tools/orphan-strings/            TOOL.md + fixtures
.agent/tools/verify-signatures/         TOOL.md (contract only — see below)
.agent/speccify/expansions.yaml         ← provenance
```

Note the second line: dependencies between skills resolve at expand
time — `macos-notarize-tauri` declares it builds on
`apple-developer-id-cert`, so that skill arrives as its own normal
skill beside it. Nothing refers back to the source anymore.

## 3. Execute: the agent implements the tools

The tool folders arrive with contracts and fixtures but no
implementations for your machine — [that's the
point](/speccify/execute/). One agent run implemented the three
release-checks tools (`macos.py`, `macos.sh`) from their contracts.

And one tool deliberately **stayed a contract**: `verify-signatures`
won't be needed until notarization, so it isn't implemented yet.
Import doesn't oblige you to build everything on day one — an
unimplemented tool is visible as such in the tools tab and in the
provenance record, not forgotten.

## 4. Evaluate: check, then trust

```sh
speccify tool check check-entitlements   # → verified
speccify tool check check-plist-keys     # → verified
speccify tool check orphan-strings       # → verified
```

Each check runs the contract's examples against the fresh
implementation ([how that works](/speccify/evaluate/)). After that,
the agent uses these skills like any local one — and logs an
`agent_run` line in the spec's history when it does.

The whole import was **one atomic commit** in 4Notice, subject
"Import skills from speccify-first-test and implement their tools" —
skills, tools, fixtures, provenance, 3× verified, all in one
reviewable step.

Next: the direction that makes this a cycle —
[exporting what 4Notice taught you](/tutorial/exporting-skills/).
