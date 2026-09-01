---
title: A plan and a board
description: Writing the plan, letting the agent slice it into tickets, and working the board.
sidebar:
  order: 4
---

Work does not start in chat. It starts as a **plan**
(what and why), becomes **tickets** (small, ordered, checkable), and
moves across the **board**. This chapter shows the real 4Notice
plan and what the agent made of it.

## 1. Write the plan — one sentence first

The plan is a markdown file, `.agent/plans/basic-app-plan.md`, with
`lifecycle: active` (only one plan is active at a time). Write it in
whatever language you think in — 4Notice's is German; the agent
doesn't care. Its core, translated:

> Four sticky notes in the four classic post-it colors. A Mac and iOS
> app, with a watch target, desktop widgets, and menu-bar quick
> access. Simple and very fast sync via ubiquitous storage.
>
> **The sentence v1.0 must make true:** four notes, the same on every
> device, instantly there — type, make it bold, done. No document, no
> folder, no saving.

That sentence is the yardstick: every scope question of the following
weeks gets measured against it.

The rest of the plan is a **feature table** — one row per feature,
each row saying precisely what it means and which ticket owns it
("iPhone: one note visible, swipe horizontally; start = pinned note …
→ N4"). Precision here is cheap; ambiguity here is a wrong build
later.

## 2. Decisions before tickets

Sketching the plan surfaced questions only the owner could answer —
deployment targets, the sync store, the purchase model and price.
They went through the [Q&A protocol](/app/questions/): asked
in chat, answered by the owner, recorded. Only then did slicing make
sense — a ticket sliced on an open question encodes a guess.

## 3. The agent slices

One instruction ("slice the plan into tickets") turned the plan into
**thirteen tickets**, N1–N13, each a file under `.agent/board/`:
rich-text editor, KV-store sync with a size budget, iPhone pager,
fonts, menu bar, widgets, watch app, trial & purchase, i18n, icon,
fastlane, release. Each is sized for **one agent run**, ordered by
`order`, and starts in `Backlog`. A real one:

```markdown
---
id: n2-rich-text-editor
title: Rich text with simple edit tools (WYSIWYG)
station: Done
created: 2026-08-23T10:28:02Z
order: 2
plan: basic-app-plan
---
## Scope
`Note.text` becomes `AttributedString`; `NoteView` edits WYSIWYG.
Toolbar per note: bold, italic, underline, heading, bullet list,
checklist. `RichText` encodes ⇄ `Data` for store and sync.

## Acceptance criteria
- Bold/italic/underline/heading/list/checklist apply to the selection
  and survive a restart
- `RichText` round-trip test (attributes survive encode/decode)
- macOS and iOS use the same editor code
```

Notice what the acceptance criteria are: **observable outcomes**, one
of them a named test — not "editor works".

## 4. Work the board

From here the loop is mechanical, and that's the point:

1. Take the **top Backlog ticket** (lowest `order`), set it to
   `In Progress` — only one ticket is ever in `In Progress`.
2. Do the work; [commit as you go](/tutorial/working-and-commits/).
3. Check every acceptance criterion; then `Done`.
4. Too big for one run? **Split it** instead of leaving it half-done.

In the Speccify app you watch the board move in real time, and the ticket's
history shows each step the agent logged:

```json
{"event_type":"station_changed","summary":"Backlog -> In Progress", …}
{"event_type":"station_changed","summary":"In Progress -> Done (rich text + format bar, 7 tests, visual check)", …}
```

Six days after slicing, N2–N11 were `Done` — editor, sync, pager,
fonts, menu bar, widgets, watch, trial, localization, icon. The next
chapter looks at what kept that pace *auditable*:
[the commits](/tutorial/working-and-commits/).
