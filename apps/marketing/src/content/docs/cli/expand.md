---
title: "speccify expand"
description: "Turn locked skills into normal, project-specific skills under .agent/."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Turn locked skills into normal, project-specific skills under .agent/.

## Usage

```bash
speccify expand [OPTIONS] [REFERENCES]...
```

## Arguments

| Argument | Pflicht |
| --- | --- |
| `references` | nein |

## Options

| Option | Beschreibung |
| --- | --- |
| `--project`, `-p` | Project directory (default: current directory). |
| `--library` | Local skill library (default: from the manifest). |
| `--offline`, `--no-offline` | Only read cached git sources, never the network. |
| `--platform` | macos, linux or windows (default: this machine). |
