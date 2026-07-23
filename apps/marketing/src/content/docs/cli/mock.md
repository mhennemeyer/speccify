---
title: "speccify mock"
description: "Generiert deterministische Mock-Komponenten (inkl. Kompositions-Kindern)."
---

{/* AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. */}

Generiert deterministische Mock-Komponenten (inkl. Kompositions-Kindern).

## Usage

```bash
speccify mock [OPTIONS] SPEC_REF
```

## Arguments

| Argument | Pflicht |
| --- | --- |
| `spec_ref` | ja |

## Options

| Option | Beschreibung |
| --- | --- |
| `--registry` | Pfad zur lokalen Registry (Layout: <scope>/<name>/<version>/spec.speccify.yaml). |
| `--out` | Ausgabe-Verzeichnis für die Mock-Dateien. |
| `--target` | Mock-Target (P2: nur 'react'). |
