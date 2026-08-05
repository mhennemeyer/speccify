---
title: "speccify conformance"
description: "Prüft pro (Spec, Target), dass Renderer + Validator + Lockfile-Hash stimmen."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Prüft pro (Spec, Target), dass Renderer + Validator + Lockfile-Hash stimmen.

## Usage

```bash
speccify conformance [OPTIONS]
```

## Options

| Option | Beschreibung |
| --- | --- |
| `--project`, `-p` | Projekt-Verzeichnis mit speccify.yaml/speccify.lock (Default: aktuelles Verz.). |
| `--target`, `-t` | Nur diese Target(s) prüfen (Default: alle Targets des Lockfiles). Wiederholbar: `-t react -t swiftui`. |
| `--registry` | Optionale Registry-Pfad-Überschreibung. |
| `--offline`, `--no-offline` | Nur Replay-Cache benutzen (Default). |
| `--cache-dir` | Replay-Cache-Pfad (Default: tests/fixtures/llm-cache im Repo bzw. $SPECCIFY_CACHE_DIR). |
