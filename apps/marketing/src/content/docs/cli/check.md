---
title: "speccify check"
description: "Check whether playbooks are still current: source age and dead links."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Check whether playbooks are still current: source age and dead links.

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
