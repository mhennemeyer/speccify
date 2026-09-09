---
title: "speccify export"
description: "Copy a project skill into a library as a general skill — the reverse of expand."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Copy a project skill into a library as a general skill — the reverse of expand.

## Usage

```bash
speccify export [OPTIONS] NAME
```

## Arguments

| Argument | Pflicht |
| --- | --- |
| `name` | ja |

## Options

| Option | Beschreibung |
| --- | --- |
| `--to` | Library checkout or folder to export into (a Speccify source). |
| `--category` | Folder inside the library; the source browser shows folders as categories. |
| `--version` | metadata.speccify.version (default: 1.0.0, or the next patch). |
| `--scope` | metadata.speccify.scope → id @scope/name (default: the library's scope). |
| `--force` | Replace SKILL.md, TOOL.md and reference.* if the skill exists. |
| `--platform` | Whose implementation becomes the reference file (default: this platform). |
| `--project`, `-p` | Project directory (default: current directory). |
