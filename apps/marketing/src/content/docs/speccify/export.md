---
title: Export
description: The reverse of expand — a skill born in a project goes to a source repo as a general skill, with its tools as contracts.
sidebar:
  order: 5
---

Sometimes the recurring thing was never in a library. You did it three
times in this project, wrote the tools for it, and the skill under
`.agent/skills/` is the only place it exists. **Export** takes it the
other way: `speccify export <skill> --to <source>` copies it into a
source checkout as `skills/<name>/` — the reverse of
[expand](/speccify/expand/).

What the command does mechanically:

- **The `## In this project` section is dropped.** It is the project's
  by definition; the next project gets a fresh one on expand.
- **The skill gets an id.** `metadata.speccify.version` (`1.0.0`, or
  the next patch when the skill already exists there) and
  `metadata.speccify.scope` (the scope the library's other skills use,
  or `--scope`) — so `speccify add @scope/name` can find it.
- **Tools travel as contracts.** Every tool the skill links to goes
  along as `tools/<tool>/TOOL.md`. The implementation you wrote here
  becomes `tools/<tool>/reference.<ext>` — a hint for the next
  implementer, never the contract. Other platforms' implementations
  stay in the project; fixtures the examples need come along.
- **The target is checked** like any library skill, and the command
  prints the `speccify add … && speccify expand …` line that records
  the origin back in your project once the export is pushed.

What no command can do is *generalise the text*. A bundle id, an
absolute path, a team id, a private host — they were right here and
are wrong everywhere else. The export ends with a list of lines that
look like that:

```text
Review before you commit — these lines look project-specific:
  SKILL.md:14  path: /Users/me/Work/App/build/App.app
  SKILL.md:15  bundle-id: com.acme.app
  tools/verify/reference.sh:3  host: https://gitlab.acme.internal/ci
```

Each becomes a placeholder `<like-this>` or goes. Placeholders are the
contract between the author and the next reader: expand reports them
as *to fill in*, so a reader is never left guessing what was specific.

Nothing is committed. The source is a git checkout — the app's
**Library** clones it, or you did — and committing and pushing is a
normal git step there, yours or the agent's. Then, back in the
project:

```sh
speccify add @acme/notarize --library "~/.speccify/sources/github.com-acme-skills"
speccify expand notarize --library "~/.speccify/sources/github.com-acme-skills"
```

Your `## In this project` section survives that re-expand, and from
now on `speccify verify` tells you when the library's version moves
on.

In the app, the **Skills** tab has an *Export…* action in the
inspector of every project skill: pick a source and a folder, and the
command lands in the agent terminal.
