---
title: "speccify verify"
description: "Check that the lockfile still matches the manifest and the actual bundles."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Check that the lockfile still matches the manifest and the actual bundles.

## Usage

```bash
speccify verify [OPTIONS]
```

## Options

| Option | Beschreibung |
| --- | --- |
| `--project`, `-p` | Project directory (default: current directory). |
| `--library` | Local playbook library (default: from the manifest). |
| `--offline`, `--no-offline` | Only read cached git sources, never the network. |
