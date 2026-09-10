---
title: Evaluate
description: Built-in mini-QA — a mechanical layer and a judgment layer, looping back on failure.
sidebar:
  order: 4
---

**Evaluate** is the built-in QA step, and it has two layers.

## The mechanical layer: `speccify tool check`

```sh
speccify tool check check-plist-keys
```

The command feeds every example from the tool's `TOOL.md` into the
implementation for this platform and compares the JSON output. Green
or red, no judgment. The examples in the contract *are* the
acceptance test:

```markdown
### a plist with a camera usage description
input: {"plist": "fixtures/Camera.plist"}
output: {"ok": true, "keys": ["NSCameraUsageDescription"]}
```

The verdict is recorded in `expansions.yaml`: a passing tool moves to
`status: verified` with a date and platform; a failing one drops back
to `implemented`. The bookkeeping is honest in both directions — if a
re-expand brings a changed contract (the spec hash differs), the
`verified` badge is *removed* until the check passes again. A tool is
never "verified" against a contract it wasn't checked against.

## The judgment layer: the agent looks for counter-evidence

Mechanical checks prove the tools match their contracts, not that the
*skill's outcome* is right. So the agent evaluates the result against
the skill's own **`Verify:` lines** (every step of a well-written
skill has one) and against the spec's acceptance criteria —
actively searching for counter-evidence, not confirmation.

- No counter-evidence found → done.
- Counter-evidence found → **new iteration**: back to
  [Expand](/speccify/expand/) if the adaptation was wrong, back to
  [Execute](/speccify/execute/) if the execution was.

Findings that turn out to be *general* — a pitfall anyone would hit,
a gap in the contract — flow back to the source repo as corrections,
so the next project expands a better skill.

See the loop run end to end in the
[walkthrough](/speccify/walkthrough/).
