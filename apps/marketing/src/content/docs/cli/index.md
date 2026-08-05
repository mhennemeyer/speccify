---
title: "CLI Reference"
description: "Übersicht aller speccify-Subcommands."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Das `speccify`-CLI bündelt alle Spec-First-Workflows. Jeder Subcommand
hat eine eigene Referenzseite:

| Command | Beschreibung |
| --- | --- |
| [`speccify add`](/cli/add/) | Fügt eine Spec-Dependency in speccify.yaml ein und aktualisiert speccify.lock. |
| [`speccify build`](/cli/build/) | Baut ein lauffähiges Projekt aus einer `kind: app`-Spec. |
| [`speccify conformance`](/cli/conformance/) | Prüft pro (Spec, Target), dass Renderer + Validator + Lockfile-Hash stimmen. |
| [`speccify init`](/cli/init/) | Legt ein neues Speccify-Projekt mit minimalem `speccify.yaml` an. |
| [`speccify lint`](/cli/lint/) | Validiert eine oder mehrere YAML-Specs gegen das Spec-Schema v0. |
| [`speccify lock`](/cli/lock/) | Löst Dependencies via MVS auf und schreibt speccify.lock (ohne Codegen-Aufruf). |
| [`speccify mock`](/cli/mock/) | Generiert deterministische Mock-Komponenten (inkl. Kompositions-Kindern). |
| [`speccify pull`](/cli/pull/) | Rendert resolved Specs aus dem Lockfile und aktualisiert Output-Hashes. |
| [`speccify search`](/cli/search/) | Sucht Specs in den konfigurierten Discovery-Indizes. |
| [`speccify verify`](/cli/verify/) | Prüft, dass Manifest, Lockfile und gerenderte Dateien zueinander passen. |
