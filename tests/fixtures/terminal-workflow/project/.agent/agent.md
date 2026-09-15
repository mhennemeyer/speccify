# Disposable terminal acceptance project

Only edit this project. Do not commit, push, publish or touch other projects.
Do not add authorship/provenance statements or co-author trailers.
Use the local `text-summary` skill and its tool contract. Project rule marker:
`RULE-LOCAL-012`. Include this marker in the spec Verification.

Work on `.agent/specs/001-summary/SPEC.md`. The user's implementation request
authorizes Backlog → Doing. Keep tasks, decisions and verification in that
file. All tasks complete means `station: Doing`, `ready: true`, because
`needs_human: true`. Never accept on behalf of the human.

Tool checks maintain `.agent/speccify/expansions.yaml`; never edit it by hand.
Use the supplied CLI or MCP runtime, and record actual command results.

If a question remains unanswered, save it under `## Questions` as
`### Q1 · open · <UTC timestamp>` and set `open_question: Q1`. When an answer
arrives, keep question and answer, record the decision, clear `open_question`
and continue. Do not ask the same answered question again.
