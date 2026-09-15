---
station: Backlog
order: 1
needs_human: true
ready: false
open_question: null
---
# Summarize Unicode text

## Why

Prove that a fresh terminal session can use local project rules, a skill
and a tool contract without context from another conversation.

## What

Implement `summarize` on this platform. Use only the standard library.
Do not modify the tool contract or implement anything outside this project.
Read `.agent/runtime.md` for the prepared CLI and real stdio MCP runtime.

## Acceptance

- A deliberately incorrect implementation fails the tool examples.
- The repaired implementation passes all four examples, including Unicode.
- CLI and MCP verification agree about consistency and readiness.
- Completed work awaits human acceptance in Doing with ready: true.

## Decisions

## Tasks

- [ ] Read project instructions, local skill and tool contract.
- [ ] Implement a deliberately wrong result and record the failing check.
- [ ] Repair the implementation and pass all contract examples.
- [ ] Compare CLI JSON and MCP verification; record results and await acceptance.

## Verification

## Questions
