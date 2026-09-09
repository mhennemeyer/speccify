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
