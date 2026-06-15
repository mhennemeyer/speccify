---
title: "speccify verify"
description: "Prüft, dass Manifest, Lockfile und gerenderte Dateien zueinander passen."
---

{/* AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. */}

Prüft, dass Manifest, Lockfile und gerenderte Dateien zueinander passen.

## Usage

```bash
speccify verify [OPTIONS]
```

## Options

| Option | Beschreibung |
| --- | --- |
| `--project`, `-p` | Projekt-Verzeichnis mit speccify.yaml/speccify.lock (Default: aktuelles Verz.). |
| `--out` | Verzeichnis mit gerenderten Dateien. |
| `--registry` | Optionale Registry-Pfad-Überschreibung. |
| `--offline`, `--no-offline` | Nur Replay-Cache benutzen (Default). |
| `--cache-dir` | Replay-Cache-Pfad (Default: tests/fixtures/llm-cache im Repo bzw. $SPECCIFY_CACHE_DIR). |
