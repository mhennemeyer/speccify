---
title: "speccify build"
description: "Baut ein lauffähiges Projekt aus einer `kind: app`-Spec."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Baut ein lauffähiges Projekt aus einer `kind: app`-Spec.

## Usage

```bash
speccify build [OPTIONS] SPEC_REF
```

## Arguments

| Argument | Pflicht |
| --- | --- |
| `spec_ref` | ja |

## Options

| Option | Beschreibung |
| --- | --- |
| `--registry` | Pfad zur lokalen Registry (Layout: <scope>/<name>/<version>/spec.speccify.yaml). |
| `--out` | Ausgabe-Verzeichnis für das Projekt. |
| `--target` | Build-Target (P4: nur 'react'). |
| `--mocks`, `--no-mocks` | Komponenten als deterministische Mocks (Default) oder als generierte Implementierungen aus dem Replay-Cache. |
| `--offline`, `--no-offline` | Nur bei `--no-mocks`: Replay-Cache statt Live-LLM. |
| `--cache-dir` | Nur bei `--no-mocks`: Verzeichnis des Replay-Caches. |
