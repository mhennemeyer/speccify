---
title: "speccify pull"
description: "Materialise the locked playbooks (including assets) into a directory."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Materialise the locked playbooks (including assets) into a directory.

## Usage

```bash
speccify pull [OPTIONS]
```

## Options

| Option | Beschreibung |
| --- | --- |
| `--project`, `-p` | Project directory (default: current directory). |
| `--out` | Where to materialise the bundles. |
| `--library` | Local playbook library (default: from the manifest). |
| `--offline`, `--no-offline` | Only read cached git sources, never the network. |
