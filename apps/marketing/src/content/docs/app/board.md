---
title: The board
description: Plans become tickets, tickets move through three stations, and history records who did what.
sidebar:
  order: 2
---

The board is a folder: `.agent/board/`, one markdown file per ticket.
The app renders it as three columns — and only three:

```text
Backlog  →  In Progress  →  Done
```

Two invariants keep it honest: **only one ticket is in
`In Progress`** at any time (the agent finishes or splits before
starting the next), and **stations are never invented** — a ticket is
in one of these three, or the app shows an error banner.

![The board: columns, KPI line, the active plan collapsed above](../../../assets/app/overview.png)

## A ticket is a file

```markdown
---
id: site-scaffold
title: Scaffold the site
station: Backlog
created: 2026-08-26T08:25:00Z
order: 1
plan: agent-fundamentals-website
---
## Scope
What this ticket covers — small enough for one agent run.

## Acceptance criteria
How both sides know it is done.
```

Three optional flags matter to you as the owner:

- `ready: true` — the agent's part is done and the ticket waits for the
  human, still in In Progress: review it, then move it to Done (or clear
  the flag with feedback in the body).
- `needs_human: true` — a human must act (a manual test, an account,
  a DNS entry). The app surfaces these so they don't sit unnoticed in
  Backlog.
- `open_question: Q1` — the agent is blocked on a question you
  haven't answered yet. See [Questions](/app/questions/).

## Where tickets come from

A fresh project has a plan and an empty board. The agent reads the
**active plan** (`lifecycle: active` — only one plan may be active),
slices it into small tickets ordered by `order`, and then works the
board: pick the top `Backlog` ticket, set it to `In Progress`, do the
work, commit, set it to `Done`. A ticket that turns out too big is
**split** into smaller ones rather than left half-done.

In the app, the active plan sits collapsible **above the board**, so
you always see what the tickets are sliced from. On the board itself:
click a card to open the **ticket detail** in the inspector on the
right — an *Overview* tab with questions and body, a *History* tab
with the timeline (below the board if the inspector is hidden);
double-click a card, or **Edit** in the inspector, to open the editor
sheet; drag & drop moves tickets between columns; **+ Ticket** adds
one. The navigator filters the board by plan, and the **needs me**
filter shows only tickets waiting on you. The Done column is grouped by
`plan`, so finished work stays legible across plans.

## History: the ticket's memory

Each ticket has an append-only log,
`.agent/board/history/<id>/index.jsonl` — one JSON line per
meaningful step:

```json
{"actor":"agent","event_type":"station_changed","summary":"Backlog -> In Progress","ticket_id":"site-scaffold","timestamp":"2026-08-26T09:05:30Z"}
```

The app logs what the app changes; **the agent logs its own steps** —
creating and moving tickets, recording answered questions, running a
skill. The event types (`ticket_created`, `station_changed`,
`ticket_edited`, `agent_run`) each get an icon in the ticket detail,
so you can reconstruct any ticket's life without reading a terminal
transcript. The board's KPI row is computed from the `agent_run`
events — runs and effective input — so the cost of the work stays
visible next to the work.

![A ticket detail: body and history timeline](../../../assets/app/ticket-detail.png)
