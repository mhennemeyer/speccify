---
title: MCP Reference
description: Speccify as an MCP server — every playbook capability available to coding agents.
---

Speccify ships an MCP server over stdio. Every tool is a thin adapter over
`speccify-core`, the same code the CLI runs — so an agent and a human never get
different answers.

```bash
uv run speccify-mcp --project /path/to/project
```

## Reading playbooks

This is the path that matters, and it is pinned by a test: an agent that has to
guess the order is an agent that gets it wrong halfway through a release.

| Tool | What it does | Key inputs |
|---|---|---|
| `playbook_list` | everything in the library: id, title, summary, step count | `library_path?` |
| `playbook_get` | one playbook: steps, sources, pitfalls, prerequisites | `reference` |
| `playbook_step` | a single step, with its sources resolved | `reference`, `step_id` |
| `playbook_asset` | a file that ships with the playbook | `reference`, `path` |
| `playbook_check` | structure plus how old every source is | `reference`, `links?` |

`reference` is a playbook id (`@scope/name`) or a git source
(`git+<url>[#<path>]`). Every one of these also takes `offline` and an optional
`library_path`.

`playbook_check` is the one to call before following a playbook: it reports
sources that have not been re-read in over 180 days. A stale playbook is worse
than none, because an agent will follow it confidently.

## Finding and pinning

| Tool | CLI equivalent | Effect |
|---|---|---|
| `search` | `speccify search` | read-only, across configured index repos |
| `lock` | `speccify lock` | writes `speccify.lock` |
| `pull` | `speccify pull` | fetches bundles into the local library |
| `verify` | `speccify verify` | read-only; re-fetches and compares hashes |

## Working next to the viewer

| Tool | What it does |
|---|---|
| `viewer_selection` | what the user has selected in the viewer, **resolved** |
| `playbook_propose` | propose a changed playbook; the user sees a diff |

`viewer_selection` returns the step itself — detail, verify line, resolved
sources — not just an id, so "why is this necessary?" can be answered without
three more calls. It needs the backend running (`./scripts/dev-up.sh`); if it
is not, the tool says so with `code=backend_unreachable` rather than failing
silently.

`playbook_propose` takes the complete new `playbook.yaml`. It is validated
immediately, so an invalid proposal never becomes a diff the user cannot apply,
and it is never written to disk — only a human clicking **Apply** does that.
Playbooks from git sources are refused: changes belong in the source
repository, as a commit and a new tag.

## Errors are answers, not exceptions

Failures come back as structured results — `verify` returns `{ok, problems[]}`,
`search` reports `code=no_index_configured`, `viewer_selection` reports
`code=backend_unreachable`. An agent can react to those; it cannot react to a
transport-level error.

## Resources

| URI | Content |
|---|---|
| `speccify://manifest` | the project's `speccify.yaml` |
| `speccify://lockfile` | the project's `speccify.lock` |

Both say what to run when the file does not exist yet, rather than returning
an error.

## Client configuration

```json
{
  "mcpServers": {
    "speccify": {
      "command": "uv",
      "args": ["run", "speccify-mcp", "--project", "/path/to/project"]
    }
  }
}
```
