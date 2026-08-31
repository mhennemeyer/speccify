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
| [`speccify check`](/cli/check/) | Check whether skills are still current: source age, dead links, best practice. |
| [`speccify expand`](/cli/expand/) | Turn locked skills into normal, project-specific skills under .agent/. |
| [`speccify init`](/cli/init/) | Create the manifest and link Claude/Codex skill dirs to .agent/skills. |
| [`speccify link`](/cli/link/) | Point agent skill directories at the canonical .agent/skills directory. |
| [`speccify lint`](/cli/lint/) | Validate skills against the Agent Skills specification. |
| [`speccify lock`](/cli/lock/) | Resolve dependencies and write speccify.lock. |
| [`speccify pull`](/cli/pull/) | Materialise the locked skills untouched, as upstream has them (default: the cache). |
| [`speccify search`](/cli/search/) | Search playbooks in the configured discovery indexes. |
| [`speccify show`](/cli/show/) | Print a skill: what it is, what it builds on, and how old its sources are. |
| [`speccify tool check`](/cli/tool-check/) | Run each tool spec's examples against the implementation for this platform. |
| [`speccify verify`](/cli/verify/) | Check that the lockfile still matches the manifest and the actual bundles. |
