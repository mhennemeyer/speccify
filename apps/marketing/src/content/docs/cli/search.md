---
title: "speccify search"
description: "Sucht Specs in den konfigurierten Discovery-Indizes."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Sucht Specs in den konfigurierten Discovery-Indizes.

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
| `--index` | Index-Quelle: lokales Verzeichnis oder 'git+<url>'. Mehrfach angebbar. |
| `--offline`, `--no-offline` | Nur den lokalen Index-Cache lesen, kein Netz. |
| `--json` | Treffer als JSON ausgeben (für Agents/Skripte). |
