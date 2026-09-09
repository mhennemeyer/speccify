---
title: "speccify add"
description: "Add a playbook dependency and update the lockfile."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Add a playbook dependency and update the lockfile.

## Usage

```bash
speccify add [OPTIONS] REFERENCE
```

## Arguments

| Argument | Pflicht |
| --- | --- |
| `reference` | ja |

## Options

| Option | Beschreibung |
| --- | --- |
| `--project`, `-p` | Project directory (default: current directory). |
| `--library` | Local playbook library (default: from the manifest). |
| `--source` | Skill source to read from and remember in speccify.yaml: a git URL (cloned by the app to ~/.speccify/sources/) or a directory. |
