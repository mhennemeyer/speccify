---
title: Skills, tools & sources
description: What your agent can do here — browsable in the app, importable from Speccify sources.
sidebar:
  order: 6
---

The skills tab shows what the agent knows how to do in *this*
project: the [skills](/fundamentals/skills/) under `.agent/skills/`,
each with its origin from `expansions.yaml`. The tools tab does the
same for the [tools](/fundamentals/tools/) under `.agent/tools/` —
the same files the agent reads, rendered for you.

![The skills tab: an expanded skill with its provenance](../../../assets/app/skills.png)

## One source of truth, many agents

`.agent/skills/` is the source; agent-specific folders are links
into it (a junction on Windows):

```text
.claude/skills → ../.agent/skills
.agents/skills → ../.agent/skills
```

Add or edit a skill under `.agent/skills/` and every agent sees it
immediately. The rule is the same for you and the agent: edit there,
never inside a dot-folder.

## Sources: skills you didn't write

Skills and tools can come from a **Speccify source** — a skills repo.
The skills tab's **Browse sources** mode shows the sources configured
for this project (one or more; the default comes from the dashboard
settings). The source's folder structure *is* the organization — its
folders are the categories you browse. Pick a skill to preview it;
**Import (expand)** types the matching
`speccify add … && speccify expand …` command into the agent
terminal, and the [expand step](/speccify/expand/) does the rest:
normal skills land in `.agent/skills/`, tool contracts in
`.agent/tools/`, and `.agent/speccify/expansions.yaml` records where
each came from, at which version, and whether each tool's
implementation is `verified` on this platform.

Two rules keep the bookkeeping sane:

- **Edit the skills and tools, not `expansions.yaml`** — the record
  is maintained by Speccify; hand-edits would make it lie.
- **Tools are pre-approved deliberately.** The host's settings
  (for Claude Code, `.claude/settings.json`) allowlist running
  what's under `.agent/tools/` — implementations are
  contract-checked, so the agent can call them without a permission
  prompt each time.

When the agent uses an expanded skill while working a ticket, it logs
an `agent_run` line in the ticket's history naming the skill and
tool — the [ticket detail](/app/board/) is the trail of what was
used; there is no separate log file.
