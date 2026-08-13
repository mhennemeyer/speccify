---
title: "speccify check"
description: "Check whether skills are still current: source age, dead links, best practice."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Check whether skills are still current: source age, dead links, best practice.

## Usage

```bash
speccify check [OPTIONS] PATHS...
```

## Arguments

| Argument | Pflicht |
| --- | --- |
| `paths` | ja |

## Options

| Option | Beschreibung |
| --- | --- |
| `--links`, `--no-links` | Also check that every source URL still resolves. |
| `--stale-days` | Warn about sources older than this. |
