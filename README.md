# Speccify

> The agent-agnostic skill and tool manager — share the contract, not the
> implementation.

**Skills** carry what you learned the hard way: plain `SKILL.md` files,
shared over Git like Go modules — no account, no central registry.
`speccify expand` copies them into a project where every coding agent finds
them. **Tools** ship as contracts, not scripts: a `TOOL.md` defines inputs,
outputs, effects and examples, your agent implements it for the machine at
hand, and `speccify tool check` proves the implementation against the
contract's examples. The **Speccify desktop app** (macOS and Windows) runs
the whole workflow on top: plans, tickets, a live board, project actions —
with Claude Code or Codex in the built-in terminal.

## Why

- What you learned in one project is not there in the next — and neither is
  the agent's knowledge.
- Ready-made scripts break on the next machine: another Python, another OS,
  a path that only existed on yours. The contract travels; the
  implementation is local.
- Agent workflows drift. Speccify keeps one file-based workflow —
  `.agent/plans/`, `.agent/board/`, questions, history — that any agent can
  follow and the app makes visible.

## The three steps

1. **Expand** — `speccify expand <skill>` copies the skill and its tool
   contracts into `.agent/`, normalized and versioned, provenance recorded
   in `.agent/speccify/expansions.yaml`.
2. **Execute** — the agent implements each `TOOL.md` for this platform
   (`macos.sh`, `windows.ps1`, …) right in the project.
3. **Evaluate** — `speccify tool check <tool>` runs the contract's examples
   against the implementation. Only passing examples make a tool
   `verified` — never a hand edit.

## Quickstart

```bash
uv sync --all-packages

uv run speccify lint skills/            # the reference skills in this repo
uv run speccify init --project ~/work/app
uv run speccify add @speccify/macos-notarize-tauri --project ~/work/app --library skills
uv run speccify expand macos-notarize-tauri --project ~/work/app --library skills
uv run speccify tool check verify-signatures --project ~/work/app
```

`speccify init` links `.claude/skills` and `.agents/skills` to the canonical
`.agent/skills`, so Claude Code and Codex read the same files. On Windows the
links are directory junctions — no admin rights needed.

## The app

Every project opens in its own window, laid out like Xcode (navigator,
content, inspector, terminal): the project files with a code editor and a
Git tab (stage, diff, commit — by you or by the agent — pull, push), the
board (file-based tickets in `.agent/board/`, one in progress at a time,
history and token counts from the agent's own `agent_run` log lines), the
active plan above it, skills and tool contracts with their per-platform
verification status, project actions with live output and charts, and an
agent terminal that already knows the project and resumes its session after
a restart. The app watches files; the agent does the work. Everything shown is
plain files, so it works with any agent and survives without the app.

## Repository layout

| Path | Purpose |
|---|---|
| `core/` | Python domain logic: skills, sources, lockfiles, expansion, tool checks |
| `cli/` | `speccify` — thin Typer adapter over `core/` |
| `mcp/` | MCP server for coding agents — same core, `skill_*`/`tool_*`/`source_*` tools |
| `crates/` | Rust MCPs: exec, discovery, parallels; shared toolbox |
| `apps/desktop/` | The Tauri 2 desktop app (macOS + Windows) |
| `apps/marketing/` | Website + docs (Astro Starlight) — <https://speccify.io> |
| `skills/` | Reference skills, each a directory with `SKILL.md` and tool contracts |
| `schema/` | JSON schemas (skill metadata, manifest, lockfile, index entry) |

## Documentation

- <https://speccify.io> — tutorial (zero to App Store), fundamentals,
  the Speccify workflow, and a tour of the app
- [`docs/git-sources.md`](./docs/git-sources.md) — sharing skills over Git,
  discovery via index repositories
- [`docs/toolkit.md`](./docs/toolkit.md) — the local MCP servers the app can
  expose (exec, discovery, owner questions)
- [`.agent/plans/`](./.agent/plans/) — the living roadmap; the repo is built
  with its own workflow (plans, board, skills), so the best documentation of
  how Speccify works is how this repository works

## License

MIT.
