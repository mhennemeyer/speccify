# Speccify agent workspace

This directory is managed with Speccify. Speccify organizes reusable skills,
their project-specific expansion, and contracts for tools that must work on
this machine. The active coding agent remains the executor.

## Canonical project files

- `.agent/skills/<name>/SKILL.md` contains normal, project-specific skills.
- `.agent/tools/<name>/TOOL.md` is a platform-independent tool contract;
  implementations live beside it as `<platform>.<ext>`.
- `.agent/speccify/expansions.yaml` records provenance and verification state.
- `.agent/plans/` and `.agent/board/` contain plans and file-based tickets when
  the project uses those workflows.
- `.agent/actions.json` contains named, reviewable project commands.

Agent-specific directories are adapters only. Claude reads `.claude/skills`;
Codex reads `.agents/skills`. Both should point at `.agent/skills` and must not
be edited as separate sources.

## Working with skills and tools

1. Read a matching skill completely before following it.
2. Treat `TOOL.md` as the contract. Inspect its schemas, effects, requirements,
   and examples before writing or changing a platform implementation.
3. Run `speccify tool check <name>` until all examples pass. Do not mark a tool
   verified by hand.
4. Use `speccify verify` to detect lockfile, bundle, expansion, and tool drift.
5. Preserve the `## In this project` section when adapting an expanded skill;
   Speccify keeps that section across re-expansion.

## MCP servers

The Speccify desktop app can expose local Discovery, Exec, and owner-question
servers. Claude configuration lives in `.mcp.json`; Codex configuration lives
in `.codex/config.toml`. Use only the configuration native to the active host.
Never copy secrets into either project file; reference environment variables.
