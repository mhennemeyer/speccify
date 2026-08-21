---
name: speccify
description: Bring a skill from a Speccify library into this project and use it in three phases
  — expand (adapt it here, implement its tools for this machine), execute, evaluate (try to
  prove it went wrong; iterate if it did). Use when a task is recurring and no installed skill
  covers it, when a skill under .agent/skills/ names a tool that has no implementation yet,
  or when the user mentions speccify, expand, tool spec, or .agent/skills.
license: MIT
compatibility: Requires the `speccify` CLI on PATH and a project with speccify.yaml
---

## Prerequisites

- `speccify --help` works. If not, stop and tell the user to install it.
- The project has a `speccify.yaml`. If not, `speccify init` creates one; then
  `speccify link` points `.claude/skills` at `.agent/skills`.
- Skills live under `.agent/skills/`, tool implementations under
  `.agent/tools/`, and both are committed. `.claude/skills` is only a link.

## 1 — Find before you research

Before working something out from scratch, look for a skill that already
holds the answer:

```sh
speccify search <words>          # across the configured libraries
speccify show @scope/name        # read it without installing
```

A skill whose description names the situation you are in is worth reading
whole. Nothing found: do the work, and afterwards consider step 5.

**Verify:** You either have a candidate skill id or you have searched and can say what you searched for.

## 2 — Expand: make it this project's skill

```sh
speccify add @scope/name         # into speccify.yaml, locks it
speccify expand                  # -> .agent/skills/<name>/, .agent/tools/<tool>/
```

`expand` resolves what the skill builds on (each becomes a sibling skill),
strips everything Speccify-specific, and prints two lists. Work through both:

1. **Placeholders** — `<bundle-id>`, `<path to .app>` and the like. Put the
   concrete values into the `## In this project` section at the end of the
   skill. Never edit above that heading: it is upstream and is replaced when
   upstream changes; your section is kept.
2. **Tools to implement** — for each `.agent/tools/<tool>/`, read `TOOL.md`.
   It is a contract: input schema, output schema, `effects`, `requires`,
   and `## Examples`. Write `<platform>.<ext>` beside it (`macos.sh`,
   `linux.py`, `windows.ps1` — stem is the platform, language is yours)
   that reads one JSON object on stdin, writes one JSON object on stdout,
   exits 0 on `ok` and non-zero with a message on stderr otherwise. A
   `reference.*` file, if present, is one implementation for one platform —
   consult it, do not assume it runs here.

Commit `.agent/` — the expanded skill and its tools are project knowledge.

**Verify:** `speccify verify` is green and no longer lists a tool as "has no implementation for this platform".

## 3 — Execute

Follow `.agent/skills/<name>/SKILL.md` step by step. Call the tools you
implemented the way the skill describes — directly, as executables; there is
no intermediary. Before the first step, open the trace (see below) with
iteration 1. When a step's `**Verify:**` line does not hold, do not push on:
note it in the trace and go to step 4 now — a later step would only bury it.

**Verify:** Each step's own `**Verify:**` line holds before you move to the next.

## 4 — Evaluate: try to prove it went wrong

Do not ask "did it work?" — ask "how would I know if it had not?" and go look.
Two layers, mechanical first:

```sh
speccify tool check              # every tool; or: speccify tool check <name>
```

It feeds each tool its `## Examples` on stdin and compares stdout with the
expected output (extra fields are fine, missing or different ones are not;
`ok: true` must come with exit 0; the output must satisfy the `outputs`
schema). All examples pass → the tool is `verified` for this platform in
`.agent/speccify/expansions.yaml`, and `speccify verify` stops mentioning it.
A mismatch is a bug in your implementation, not in the example. Examples
run inside `.agent/tools/<name>/`, so fixtures they name live there.

Then the part no runner can do — the *result of the skill*:

- Re-run every `**Verify:**` line of the skill against the actual result, not
  against your memory of having done the step.
- Look for the failure the skill warns about in its pitfalls, and for the one
  it does not mention but your project makes likely.
- Check what the skill promised at the end (its acceptance, its last Verify)
  from outside: open the artefact, run the command a stranger would run.

**The iteration rule.** Found nothing after genuinely trying: done — close
the trace with `ok`. Found something: decide what was wrong —

- the *adaptation*: a placeholder, the project section, a tool → back to
  step 2, fix it, re-run `speccify tool check`;
- the *execution*: a step skipped or done against its Verify → back to step 3;

— add an iteration to the trace, and evaluate again. Three iterations without
progress means the skill itself is wrong: stop and say so (step 5).

**Verify:** You can name what you tried to break and what happened, and the trace says so.

### The trace

One entry per skill use in the project log (`.agent/log.md` if the project
has one, otherwise the place the project keeps its history), appended, never
rewritten:

```markdown
### 2026-08-21 · macos-notarize-tauri 1.0.0 · iteration 2 · ok
- tools: verify-signatures verified (macos.sh, 3/3)
- tried: re-ran `spctl --assess` on the stapled .dmg; opened it from a fresh user account
- found: iteration 1 — helper binary signed after the bundle, notarization rejected it
- fixed: adaptation — `## In this project` now names the sidecar order
```

Date, skill and version (from `expansions.yaml`), iteration number, verdict
(`ok` | `open` | `abandoned`). Then what the tools said, what you tried, what
you found, and whether the fix was adaptation or execution. When something
goes wrong a month later, that entry is what says where to look.

## 5 — Give back what was general

If the evaluation taught you something that is true for everyone, not just
for this project, it belongs upstream: in the skill's source repository, as
a step, a pitfall, or a sharper example in a tool spec — an example that
would have caught your bug is the best gift. Project-specific knowledge
stays in `## In this project`.

## Pitfalls

- Editing above `## In this project` — lost on the next `speccify expand`.
- Copying a `reference.sh` and calling it the implementation without running
  the examples — the reason the contract exists is that references do not
  travel.
- Implementing a tool as a function inside your own code instead of as an
  executable: then nothing can check it against the examples.
- Calling a tool verified because its examples pass while the skill's own
  Verify lines were never re-run — `tool check` proves the tool, not the result.
- Evaluating from memory ("I did that step") instead of from the artefact.

## In this project

<!-- Everything above is upstream and is replaced on re-expand; this
     section is yours and is kept. Fill in what is specific here. -->

- _Nothing project-specific yet._
