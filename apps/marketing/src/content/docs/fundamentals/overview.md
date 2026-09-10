---
title: Overview
description: The .agent folder — one place in the repository where plan, board, skills, and tools live.
sidebar:
  order: 1
---

Everything the workflow needs lives in one folder at the root of the
repository:

```text
.agent/
├── agent.md          # the workflow contract — how the agent works here
├── specs/            # one folder per piece of work: SPEC.md with tasks as checkboxes
│   ├── <slug>/       #   + history.jsonl, the append-only log
│   └── archive/      # optional historical content; new Done specs stay in place
├── playbooks/        # standing procedures (release, deploy) — reused, not worked off
├── skills/           # reusable instructions for the agent
│   └── <name>/SKILL.md
└── tools/            # small checked programs the skills call
    └── <name>/TOOL.md + one implementation per platform
```

Three properties make this work:

- **Plain files.** Specs, playbooks, skills, and tool contracts are
  markdown with YAML frontmatter; history is JSONL. Everything is
  reviewable in a diff and survives any tool change.
- **Agent-agnostic.** `agent.md` is the single source of truth for the
  workflow. Agent-specific entry points (`CLAUDE.md`, `AGENTS.md`)
  only point to it, and agent-specific skill folders such as
  `.claude/skills` are symlinks into `.agent/skills/` — add a skill
  once, every agent sees it.
- **Two readers, one state.** The agent reads and writes these files
  from the terminal; the [Speccify app](/app/overview/)
  renders the same files for the owner. There is no synchronization
  problem because there is nothing to synchronize.

The rest of this section covers the building blocks in turn:
[skills](/fundamentals/skills/) (what the agent knows how to do),
[tools and tool specs](/fundamentals/tools/) (small programs with a
strict, testable contract), and [MCPs](/fundamentals/mcps/) (how an
agent reaches beyond the file system).
