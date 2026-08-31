---
name: ticket-ask
description: Record an open question on the current board ticket. Use when a run must end while waiting for the human.
---

# ticket-ask

Follow "Asking the human" in `.agent/agent.md`. In short: append the question
to the ticket body under `## Questions` as `### Q<n> · open · <timestamp>`,
set `open_question: Q<n>` in the front matter (oldest open question), and
leave the ticket in `Doing`. Never reuse question numbers.
