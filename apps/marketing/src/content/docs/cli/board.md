---
title: "speccify board"
description: "Render progress from the spec register into one static HTML page."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Render progress from the spec register into one static HTML page.

## Usage

```bash
speccify board [OPTIONS]
```

## Options

| Option | Beschreibung |
| --- | --- |
| `--out`, `-o` | Target HTML file (parents are created). |
| `--specs` | Specs folder (default: <project>/.agent/specs, i.e. the `specs` branch checkout). |
| `--project` | Project directory. |
| `--title` | Page title (default: project folder name). |
| `--source` | Label for the data source shown on the page, e.g. `specs@<commit>`. |
| `--no-archive` | Leave `archive/` out. |
