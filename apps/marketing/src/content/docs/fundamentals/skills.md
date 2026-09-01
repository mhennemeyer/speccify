---
title: Skills
description: Reusable instructions for the agent — one folder per skill, one SKILL.md as the source of truth.
sidebar:
  order: 2
---

A **skill** is a reusable instruction set for the agent: how to run
the pre-release checks, how to pick the next ticket, how to ask the
owner a question. Each skill is a folder under `.agent/skills/` with a
`SKILL.md` inside — frontmatter says *when* to use it, the body says
*how*.

## A minimal, real skill

This is `ticket-next` — the skill that drives the board, verbatim:

```markdown
---
name: ticket-next
description: Pick the next backlog ticket, move it to In Progress and work it
  to completion. Use when the user says "next ticket", "weiter", or asks
  what to work on.
---

Follow the board workflow in `.agent/agent.md`.

1. Read `.agent/board/*.md`. Refuse to start if a ticket is already in
   `In Progress` — finish or split that one first.
2. Pick the `Backlog` ticket with the lowest `order`.
3. Set `station: In Progress`, then implement it.
4. Verify against the ticket's acceptance criteria before setting
   `station: Done`.

If a decision is needed that only the owner can make, use the
`ticket-ask` skill instead of guessing.
```

Two things to notice:

- The **description** is written for the agent's trigger decision:
  it names the situations ("next ticket", "weiter") in which the skill
  applies. A vague description means the skill never fires.
- The **body** is a procedure with a refusal condition and a
  verification step — not prose about the topic. Skills that read like
  articles get skimmed; skills that read like checklists get followed.

## Anatomy of a larger skill

Production skills grow a few more parts. `release-checks` (from the
Speccify app project) checks an app bundle before an App Store upload;
its structure is worth copying:

```markdown
---
name: release-checks
description: Pre-release checks for a sandboxed Apple app bundle —
  entitlements, Info.plist usage keys and localization leftovers that
  App Review would ask about. Use before tagging a release, before an
  App Store upload, or when asked whether the bundle is clean.
license: MIT
compatibility: macOS with Xcode command line tools (codesign) and python3.
---

Three tools do the looking; each takes one JSON object on stdin and
answers with one JSON object on stdout (the contract is the `TOOL.md`
beside each). The tools only make lists visible — deciding what
belongs is the reviewer's job, and the answer is a short report,
never a silent fix.

## 1 — Entitlements of the built bundle
...run [check-entitlements](../../tools/check-entitlements/TOOL.md)...
**Verify:** the list contains only entitlements you can name a feature for.

## 2 — Usage descriptions and background modes
...

## Pitfalls
- Running step 1 on a Debug build with different entitlements than
  the Release configuration — check the bundle you will ship.
...

## In this project
- Bundle: build with `sh scripts/app-build.sh`; ...
```

The recurring parts:

- **Steps, each with a `Verify:` line** — the agent knows when a step
  is done, not just what to do.
- **Links to [tools](/fundamentals/tools/)** as relative paths
  (`../../tools/<name>/`) — the skill *decides and reports*, the tool
  *measures*. Keeping judgment in the skill and mechanics in a checked
  tool is the core division of labor.
- **A `Pitfalls` section** — mistakes the skill's author has already
  made, so the agent doesn't repeat them.
- **An `In this project` section** — the generic procedure stays
  reusable; project-specific paths and expectations live at the end.

## Where skills live, and why symlinks

`.agent/skills/` is the **source**. Agent products expect their own
folders (Claude Code reads `.claude/skills/`), so those are symlinks:

```text
.claude/skills → ../.agent/skills
```

Add or edit a skill under `.agent/skills/` and every agent sees the
change immediately. Never edit inside a dot-folder: the edit lands in
the same file anyway — or breaks the link. Skills can also be
installed from a Speccify source; how that
works is covered in the [Speccify section](/speccify/overview/).
