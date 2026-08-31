---
name: ticket-next
description: Work the next board ticket. Use when the user says "next ticket", "ticket next", or asks to continue board work.
---

# ticket-next

Follow the "Board workflow" section in `.agent/agent.md` — it is the single
source of truth. In short: take the topmost `Backlog` ticket (smallest
`order`), move it to `Doing` (only one ticket in `Doing`), do the work, write
history, finish with `Done` or `ready: true`. If `Backlog` is empty, slice new
tickets from the active plan first.
