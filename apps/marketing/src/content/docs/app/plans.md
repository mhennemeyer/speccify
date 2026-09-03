---
title: Plans & playbooks
description: A plan is what the agent slices into tickets — one active at a time. A playbook is a standing procedure you run again and again.
sidebar:
  order: 3
---

Two kinds of long-form text live next to the board, and the app keeps
them apart on purpose:

- A **plan** describes a piece of work. It gets sliced into tickets,
  worked off, and is then *done*. `.agent/plans/<name>.md`.
- A **playbook** describes a procedure — release, deploy, onboarding a
  machine. It never finishes; you run it whenever the occasion comes
  around. `.agent/playbooks/<name>.md`.

Both are plain markdown files, committed with the code, and both end
up in the agent's terminal the same way: **Copy as prompt**.

## Plans

A plan has a small front matter and a body. The body is free
markdown — the app renders it, the agent reads it. The title is the
first heading; the file name is the reference tickets use (`plan:
<stem>` in the ticket front matter).

```markdown
---
lifecycle: active
status: Building — P1 delivered, P2 in progress
---
# Project window

## Goal
…

## Milestones
…
```

### Lifecycle: exactly one plan is active

`lifecycle` is one of `draft`, `active`, `onHold`, `done`, `research`.
The invariant the app enforces: **at most one plan is `active`**. That
is the plan the agent slices tickets from, and the one shown
collapsible above the board.

- **Activate** sets a plan to `active` and parks the previously active
  one on `onHold` in the same step. The app tells you which file it
  parked.
- **Archive** moves a plan to `.agent/plans/archive/` and sets
  `lifecycle: done`. Finished plans stay in the repository — the
  Plans tab lists the archive separately, so the working list stays
  short.
- Anything the app does not know in the front matter (session ids,
  custom fields) is preserved byte for byte. The app only ever
  rewrites the lines it changes.

### The editor

Open a plan and switch to **Edit**: the structured fields `lifecycle`
and `status` sit above a plain text area with the body. Save writes
the file; the agent's next run reads it. The same editor is what you
use to add a new milestone or to note a decision in the plan itself,
so the plan stays the single source of what was decided.

### Escalation: the agent needs you

An agent that hits something it must not decide alone — a
contradiction in the plan, a migration that would delete data, a
missing account — writes an `escalation:` into the plan's front
matter, either as one line or as a block:

```yaml
escalation:
  reason: Migration would drop the users table — confirm or change the plan
  raisedBy: agent
  at: 2026-09-03T09:12:00Z
```

The Plans tab shows a **red banner** with the reason on that plan.
Read it, act on it (edit the plan, answer in the terminal), then click
**Resolve** — that removes exactly these lines and nothing else.
Escalations are for the plan level; a question about a single ticket
goes through [Questions](/app/questions/) instead.

### Copy as prompt

**Copy as prompt** puts the plan on the clipboard as a markdown block
with its path as the first line:

````markdown
`.agent/plans/project-window.md`

```md
# Project window
…
```
````

Paste it into the agent terminal and add what you want done — "slice
milestone P3 into tickets", "check whether this is still consistent
with the board". The path reference lets the agent open the file
itself if it needs more than the excerpt. The same button exists on
tickets and playbooks; the fence length is computed against backticks
in the content, so code blocks inside the plan survive the trip.

## Playbooks

Playbooks are the procedures you would otherwise keep in a wiki or in
your head: *how we cut a release*, *how a new machine gets set up*,
*how we roll back a deploy*. A playbook file is a markdown body with
an optional `description` in the front matter; the title is the first
heading.

```markdown
---
description: From tag to published release, macOS and Windows
---
# Release

1. Bump the version, commit.
2. Tag `vX.Y.Z` and push the tag — the release workflow builds
   both platforms into a draft release.
3. Check the draft: signed dmg, notarization ticket stapled.
4. Publish; update the download page.
```

The **Playbooks** tab sits between Board and Plans. **+ Playbook**
creates a file from a name (umlauts and spaces become a slug), the
editor maintains description and body, and **Copy as prompt** hands
the procedure to the agent exactly like a plan. Deleting a playbook
asks first — playbooks are the kind of file you regret losing.

What playbooks deliberately do **not** have: a lifecycle, a station, an
active flag. A plan is done when its tickets are done; a playbook is
never done. If you find yourself wanting to check off steps in a
playbook, the occasion is a plan — create one and reference the
playbook from it.

## Plans, playbooks, skills — which is which?

- A **skill** teaches the agent *how* to do a kind of task, on any
  project; it comes from a [Speccify source](/speccify/overview/) and
  triggers on its own.
- A **playbook** says how *this project* runs a recurring procedure;
  you hand it to the agent when the occasion arises.
- A **plan** says what *this project* builds next; the agent slices it
  into tickets on the [board](/app/board/).
