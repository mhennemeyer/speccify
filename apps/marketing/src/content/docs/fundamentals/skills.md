---
title: Skills
description: Reusable instructions for the agent — one folder per skill, one SKILL.md as the source of truth.
sidebar:
  order: 2
---

A **skill** is a reusable instruction set for the agent: how to run
the pre-release checks, how to work the next spec, how to ask the
owner a question. Each skill is a folder under `.agent/skills/` with a
`SKILL.md` inside — frontmatter says *when* to use it, the body says
*how*.

## A minimal, real skill

This is `spec-next` — the skill the app installs to drive the specs
board, verbatim:

```markdown
---
name: spec-next
description: Work the next spec. Use when the user says "next spec", "spec next", names a spec to start, or asks to continue the board.
---

# spec-next

Follow the "Spec workflow" section in `.agent/agent.md` — it is the single
source of truth. In short: take the spec the human moved to `Doing` (or the
topmost `Backlog` spec if the human asked you to start it), attack the spec
for gaps before building, work through `## Tasks` ticking as you go, write
`## Verification` and an `agent_run` history line, finish with
`station: Done` or `ready: true`. One spec in `Doing` per session.
```

Two things to notice:

- The **description** is written for the agent's trigger decision:
  it names the situations ("next spec", a named spec) in which the
  skill applies. A vague description means the skill never fires.
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
