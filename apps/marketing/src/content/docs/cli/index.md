---
title: "CLI Reference"
description: "Übersicht aller speccify-Subcommands."
---

<!-- AUTOGENERIERT via scripts/gen_cli_docs.py aus `speccify --help` — nicht von Hand editieren. -->

Das `speccify`-CLI bündelt alle Spec-First-Workflows. Jeder Subcommand
hat eine eigene Referenzseite:

| Command | Beschreibung |
| --- | --- |
| [`speccify add`](/cli/add/) | Add a playbook dependency and update the lockfile. |
| [`speccify check`](/cli/check/) | Check whether playbooks are still current: source age and dead links. |
| [`speccify init`](/cli/init/) | Create a speccify.yaml for a project that consumes playbooks. |
| [`speccify lint`](/cli/lint/) | Validate playbooks: schema, cross-references and assets. |
| [`speccify lock`](/cli/lock/) | Resolve dependencies and write speccify.lock. |
| [`speccify pull`](/cli/pull/) | Materialise the locked playbooks (including assets) into a directory. |
| [`speccify search`](/cli/search/) | Search playbooks in the configured discovery indexes. |
| [`speccify show`](/cli/show/) | Print a playbook, or a single step of it. |
| [`speccify verify`](/cli/verify/) | Check that the lockfile still matches the manifest and the actual bundles. |
