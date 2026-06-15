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
| `--offline`, `--no-offline` | Nur Replay-Cache benutzen (Default). Mit --no-offline wird bei Cache-Miss ein Live-Bedrock-Call gemacht (AWS-Credentials aus Umgebung/.env) und das Ergebnis in den Cache geschrieben. |
| `--cache-dir` | Replay-Cache-Pfad (Default: tests/fixtures/llm-cache im Repo bzw. $SPECCIFY_CACHE_DIR). |
