---
title: 'Walkthrough: release-checks'
description: One real skill, end to end — from a source repo to three verified tools in a shipping project.
sidebar:
  order: 6
---

The `release-checks` skill audits a sandboxed macOS app before an App
Store upload: entitlements, `Info.plist` usage keys, leftover
localization strings. Here is its actual path into the Speccify app
project on 2026-08-23.

## Starting point

The source repo holds the skill and **three tool specs** — contracts
only, no implementations:

```text
github.com/mhennemeyer/speccify-first-test
└── skills/release-checks/
    ├── SKILL.md
    └── tools/
        ├── check-entitlements/TOOL.md
        ├── check-plist-keys/TOOL.md
        └── orphan-strings/TOOL.md
```

## Expand

`speccify expand release-checks` materialized the skill into the
project and recorded the provenance:

```yaml
release-checks:
  source: git+https://github.com/mhennemeyer/speccify-first-test#skills/release-checks
  version: 1.0.0
  expanded: '2026-08-23'
  tools: [check-entitlements, check-plist-keys, orphan-strings]
```

The skill arrived as a normal `SKILL.md` under `.agent/skills/`, and
gained an `## In this project` section with the concrete facts of
*this* app: how to build the bundle, where `Info.plist` and the
string catalog live, and which entitlements are expected for the 1.0
release — "sandbox, network.client, files.user-selected.read-write,
bookmarks.app-scope — nothing else." The upstream body stayed
untouched.

## Execute

The agent implemented each contract for this machine:

| Tool                 | Implementation | Why that language                  |
| -------------------- | -------------- | ---------------------------------- |
| `check-entitlements` | `macos.sh`     | `codesign` does the real work      |
| `check-plist-keys`   | `macos.py`     | plist parsing wants a real parser  |
| `orphan-strings`     | `macos.py`     | walks sources + a string catalog   |

The skill's `Pitfalls` section preserves one lesson for exactly this
step: a shell implementation that reads stdin twice — a
`python3 - <<EOF` heredoc after `$(cat)` — silently swallows the
input JSON. Use a real `.py` file. That is the function of pitfall
sections: the next agent doesn't rediscover the problem.

## Evaluate

`speccify tool check` ran each contract's examples against the
implementations until all passed. The record now reads, per tool:

```yaml
platforms:
  macos:
    file: macos.py
    status: verified
    checked: '2026-08-23'
```

Then the judgment layer: running the *skill* against the real app and
checking its `Verify:` lines — every entitlement named a shipping
feature, the plist keys had owners, and each orphaned string
candidate was confirmed or explained rather than blindly deleted
(interpolated keys are false positives by design; the skill says so).

## What shipped

Three verified tools and one adapted skill, all committed in the
project — usable from now on by any agent, with no Speccify runtime
required. And because the contracts, fixtures, and provenance are all
in the repo, the next platform (or the next project) starts from the
same source and repeats only the steps that are actually
platform-specific.
