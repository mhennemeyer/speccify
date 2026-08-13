---
title: "speccify show"
description: "Print a skill: what it is, what it builds on, and how old its sources are."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Print a skill: what it is, what it builds on, and how old its sources are.

## Usage

```bash
speccify show [OPTIONS] REFERENCE
```

## Arguments

| Argument | Pflicht |
| --- | --- |
| `reference` | ja |

## Options

| Option | Beschreibung |
| --- | --- |
| `--project`, `-p` | Project directory (default: current directory). |
| `--library` | Local skill library (default: from the manifest). |
| `--offline`, `--no-offline` | Only read cached git sources, never the network. |
| `--json` | Emit JSON (for agents and scripts). |
