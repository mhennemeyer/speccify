---
title: Execute
description: The agent implements each tool on site from its contract, then follows the skill.
sidebar:
  order: 3
---

**Execute** is the agent's part. Expand left behind a task list —
typically *"n tools to implement for this platform"* — and a
`TOOL.md` contract in each tool folder. The agent now writes the
platform file beside each contract:

```text
.agent/tools/check-plist-keys/
├── TOOL.md        ← the contract (came from the source)
├── fixtures/      ← test files the contract's examples refer to
└── macos.py       ← written here, by the agent, for this machine
```

The contract fixes everything that matters — input schema, output
schema, declared effects, worked examples — so "implement this" is a
tightly bounded task:

- **The wire format is non-negotiable:** one JSON object on stdin,
  one JSON object on stdout, exit 0 when `ok` is true.
- **The language is free.** On this machine it was `python3`
  (`macos.py`) for plist parsing and a shell script (`macos.sh`)
  where `codesign` does the real work. Another platform gets its own
  file — `windows.ps1` next to `macos.py` — and **both are
  committed**, so the next machine of the same platform implements
  nothing.
- **Error cases are part of the contract.** If the spec's examples
  include a missing-file case returning `ok: false` with an `error`
  string, the implementation must do exactly that.

The iteration rule: implement, then run
[`speccify tool check`](/speccify/evaluate/) — and keep going
**until every example passes**. The agent does not declare a tool
done; the check does.

Once the tools stand, executing the *skill* is nothing special: the
agent follows the expanded `SKILL.md` step by step, calling the tools
it now trusts, exactly as described under
[Skills](/fundamentals/skills/). Speccify adds only a **trace** —
which skill ran, which iteration, when — so that later there is an
answer to "what did it actually do?".

Whether the result is any good is the question
[Evaluate](/speccify/evaluate/) answers.
