---
title: "speccify add"
description: "Fügt eine Spec-Dependency in speccify.yaml ein und aktualisiert speccify.lock."
---

{/* AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. */}

Fügt eine Spec-Dependency in speccify.yaml ein und aktualisiert speccify.lock.

## Usage

```bash
speccify add [OPTIONS] SPEC_REF
```

## Arguments

| Argument | Pflicht |
| --- | --- |
| `spec_ref` | ja |

## Options

| Option | Beschreibung |
| --- | --- |
| `--project`, `-p` | Projekt-Verzeichnis mit speccify.yaml (Default: aktuelles Verzeichnis). |
| `--registry` | Optionale Registry-Pfad-Überschreibung. |
| `--member`, `-m` | Workspace-Member (Verzeichnisname unter dem Glob), in dessen speccify.yaml geschrieben wird. Default: CWD-Detection. |
