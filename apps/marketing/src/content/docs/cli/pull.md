---
title: "speccify pull"
description: "Rendert resolved Specs aus dem Lockfile und aktualisiert Output-Hashes."
---

{/* AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. */}

Rendert resolved Specs aus dem Lockfile und aktualisiert Output-Hashes.

## Usage

```bash
speccify pull [OPTIONS]
```

## Options

| Option | Beschreibung |
| --- | --- |
| `--project`, `-p` | Projekt-Verzeichnis mit speccify.yaml/speccify.lock (Default: aktuelles Verz.). |
| `--out` | Ausgabeverzeichnis für gerenderte Dateien. |
| `--target` | Codegen-Target (Default: Target aus Lockfile). |
| `--registry` | Optionale Registry-Pfad-Überschreibung. |
| `--offline`, `--no-offline` | Nur Replay-Cache benutzen (Default). Mit --no-offline würde ein Live-LLM-Call bei Cache-Miss erlaubt; in 5b nicht verdrahtet. |
| `--cache-dir` | Replay-Cache-Pfad (Default: tests/fixtures/llm-cache im Repo bzw. $SPECCIFY_CACHE_DIR). |
