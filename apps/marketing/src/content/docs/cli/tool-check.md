---
title: "speccify tool check"
description: "Run each tool spec's examples against the implementation for this platform."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Run each tool spec's examples against the implementation for this platform.

## Usage

```bash
speccify tool check [OPTIONS] [NAMES]...
```

## Arguments

| Argument | Pflicht |
| --- | --- |
| `names` | nein |

## Options

| Option | Beschreibung |
| --- | --- |
| `--project`, `-p` | Project directory (default: current directory). |
| `--platform` | macos, linux or windows (default: this machine). |
| `--timeout` | Seconds each example may take before it fails. |
| `--json` | Print the full report as JSON. |
