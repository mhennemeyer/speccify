---
name: spec-ask
description: Record an open question on the current spec. Use when a run must end while waiting for the human.
---

# spec-ask

Follow "Asking the human" in `.agent/agent.md`. In short: append the question
to the spec body under `## Questions` as `### Q<n> · open · <timestamp>`, set
`open_question: Q<n>` in the front matter (oldest open question), and leave
the spec in `Doing`. Never reuse question numbers.
