---
title: Tools & Tool Specs
description: Small programs with a strict contract — JSON in, JSON out, and a TOOL.md that makes them checkable.
sidebar:
  order: 3
---

A **tool** is a small program a skill can call: list the entitlements
of an app bundle, find orphaned localization keys, check a plist.
What makes it a *tool* rather than a loose script is the **spec**: a
`TOOL.md` beside the implementation that states the contract precisely
enough to be checked by machine.

## The convention

- One folder per tool under `.agent/tools/<name>/`.
- `TOOL.md` is the **contract**: input and output as JSON Schema,
  declared `effects` and `requires`, and worked examples.
- Beside it, **one implementation per platform**: `macos.py`,
  `macos.sh`, `linux.py`, … — whatever the platform needs.
- The wire format is always the same: **one JSON object on stdin, one
  JSON object on stdout**, exit code 0 when `ok` is true.
- Tools are project-wide. Several skills may share one tool; a skill
  links to it as `../../tools/<name>/`.

## A real contract

`check-plist-keys` from the Speccify app project — the full `TOOL.md`:

```markdown
---
name: check-plist-keys
description: Lists usage-description and background keys in an
  Info.plist — every entry must belong to a shipped feature.
inputs:
  type: object
  required: [plist]
  additionalProperties: false
  properties:
    plist:
      type: string
      description: Path to the Info.plist, relative to the tool
        directory or absolute.
outputs:
  type: object
  required: [ok, keys]
  properties:
    ok: {type: boolean}
    keys: {type: array, items: {type: string}, description: Matching
      keys (UsageDescription, NSUbiquitousContainers,
      UIBackgroundModes), sorted.}
    error: {type: string}
effects: reads the plist; writes nothing
requires: python3
runtime: any
---

## Behaviour

Read the plist and report every key that App Review would ask about:
all `*UsageDescription` keys, `NSUbiquitousContainers` and
`UIBackgroundModes`. An empty list is a valid, good answer. A missing
or unreadable file is `ok: false`.

## Examples

### a plist without any such keys
input: {"plist": "fixtures/Clean.plist"}
output: {"ok": true, "keys": []}

### a plist with a camera usage description
input: {"plist": "fixtures/Camera.plist"}
output: {"ok": true, "keys": ["NSCameraUsageDescription"]}

### missing file
input: {"plist": "fixtures/Missing.plist"}
output: {"ok": false, "keys": [], "error": "cannot read fixtures/Missing.plist"}
```

Each part has a function:

- **`inputs` / `outputs` as JSON Schema** — not prose. An agent (or a
  person) can validate a call before making it.
- **`effects` and `requires`** — one line each, so a reviewer knows
  what running this can touch and what must be installed.
- **`## Examples` are test cases**, not decoration. Each names a
  fixture that ships in the tool folder. `speccify tool check
  check-plist-keys` runs every example against the implementation and
  compares the JSON — the examples *are* the acceptance test.
- **The error case is part of the contract.** A missing file returns
  `ok: false` with an `error` string; it does not crash and does not
  divert to stderr.

## Calling a tool

From a shell (and from a skill's instructions), a call looks like:

```sh
echo '{"plist": "fixtures/Camera.plist"}' | python3 .agent/tools/check-plist-keys/macos.py
# → {"ok": true, "keys": ["NSCameraUsageDescription"]}
```

One pitfall from practice, recorded in the skill that uses these
tools: a shell implementation that reads stdin twice — for example a
`python3 - <<EOF` heredoc after `$(cat)` — silently eats the JSON.
Prefer a real `.py` file over inline heredocs.

## Why the split between skill and tool matters

A skill says *when* to run a check and *what the result means*; a tool
*measures*. The measuring part is deterministic and machine-checked,
so an agent cannot quietly drift on it — if the implementation and the
contract disagree, `speccify tool check` fails. Judgment stays where
it belongs, in the [skill](/fundamentals/skills/) and ultimately with
the owner. How a tool goes from contract to checked implementation is
the subject of the [Speccify section](/speccify/overview/).
