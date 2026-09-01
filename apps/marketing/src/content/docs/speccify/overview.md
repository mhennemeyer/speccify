---
title: Overview
description: Share the contract, not the implementation — Speccify's expand, execute, evaluate loop.
sidebar:
  order: 1
---

Finished scripts don't travel. A `.py` or `.sh` that works on one
machine breaks on the next: Python version, shell, path separators,
missing binaries — and the receiver ends up patching a stranger's
file. Speccify's answer is to share **skills with tool specs** instead
of skills with scripts:

> A skill describes *what* to do; a tool spec describes exactly *what
> a tool must be able to do* — and the agent programs it **on site**,
> in whatever runs on that machine. What is shared is the contract,
> not the implementation.

A spec also forces a precision that a finished script keeps implicit:
inputs, outputs, side effects, examples. A script says *how*; a spec
says *what* — and *what* ages more slowly.

## Two worlds

A skill exists in two clearly separated forms:

|            | In the **source** (a skills repo)          | In the **project** (`.agent/`)                 |
| ---------- | ------------------------------------------ | ---------------------------------------------- |
| Form       | `SKILL.md` + Speccify metadata + tool specs | perfectly normal skills — plain markdown       |
| References | `uses` points at other skills              | resolved: each referenced skill sits alongside |
| Tools      | spec only (`TOOL.md`)                      | **implemented**, one variant per platform      |
| Placeholders | generic                                  | concrete for this project                      |
| Git        | in the source repo                         | **committed** in the project repo              |

The expanded result no longer needs Speccify to function — it is just
files in `.agent/`, exactly as described in the
[Fundamentals](/fundamentals/overview/).

## The three-step loop

1. **[Expand](/speccify/expand/)** — the transition from source to
   project: resolve references, strip metadata, concretize
   placeholders, copy the tool contracts, record provenance.
2. **[Execute](/speccify/execute/)** — the agent implements each tool
   for this platform from its contract, and follows the skill.
3. **[Evaluate](/speccify/evaluate/)** — mechanical checks
   (`speccify tool check` runs the contract's examples) plus the
   agent's own search for counter-evidence. Failures loop back.

The [walkthrough](/speccify/walkthrough/) follows one real skill —
`release-checks` — through all three steps.
