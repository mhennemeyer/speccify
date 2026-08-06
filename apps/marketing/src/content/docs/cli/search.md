---
title: "speccify search"
description: "Search playbooks in the configured discovery indexes."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Search playbooks in the configured discovery indexes.

## Usage

```bash
speccify search [OPTIONS] [QUERY]
```

## Arguments

| Argument | Pflicht |
| --- | --- |
| `query` | nein |

## Options

| Option | Beschreibung |
| --- | --- |
| `--index` | Index source: local directory or 'git+<url>'. Repeatable. |
| `--offline`, `--no-offline` | Only read the local index cache, never the network. |
| `--json` | Emit hits as JSON (for agents and scripts). |
