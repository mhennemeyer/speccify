---
title: "speccify show"
description: "Print a playbook, or a single step of it."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Print a playbook, or a single step of it.

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
| `--step` | Show only this step. |
| `--project`, `-p` | Project directory (default: current directory). |
| `--library` | Local playbook library (default: from the manifest). |
| `--offline`, `--no-offline` | Only read cached git sources, never the network. |
| `--json` | Emit JSON (for agents and scripts). |
