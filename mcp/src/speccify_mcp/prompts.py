"""MCP-Prompts für Speccify (Phase 1c Step 4).

Bewusst klein gehalten: nur ein `add-spec`-Prompt als Vorlage für
Coding-Agents (Junie/Claude Code/Cursor), wie eine neue Spec in ein
Projekt aufgenommen wird. Wir lernen die Prompt-Form in Phase 1d.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .server import ServerConfig

ADD_SPEC_PROMPT_NAME = "add-spec"

_TEMPLATE = """\
Add the Speccify spec `{spec_ref}` to the project at `{project_root}` \
and render its output into `{out_dir}`.

Use the MCP tools in this order (each tool mirrors the equivalent \
`speccify` CLI subcommand):

1. Call `resolve` to confirm the dependency closure for `{spec_ref}`.
2. Call `lock` to write `speccify.lock` (no arguments needed; the \
server is bound to the project root).
3. Call `pull` with `out_dir={out_dir}` to render the locked specs \
into the target framework. Stay offline (the default) unless the \
user explicitly requested a fresh LLM call.
4. Call `verify` with the same `out_dir` to check for drift between \
manifest, lockfile, and the rendered files on disk. A green run \
returns `{{"ok": true, "problems": []}}`.

If any step fails, report the structured error to the user verbatim — \
do not rewrite the rendered code by hand. All code is generated from \
the spec; if the output looks wrong, the spec is the source of truth."""


def register_prompts(server: FastMCP, config: ServerConfig) -> None:
    """Registriert den `add-spec`-Prompt auf `server`."""

    @server.prompt(
        name=ADD_SPEC_PROMPT_NAME,
        description=(
            "Guide an AI coding agent through adding a Speccify spec "
            "to the current project: resolve → lock → pull → verify."
        ),
    )
    def add_spec(spec_ref: str, out_dir: str = "./src/components") -> str:
        return _TEMPLATE.format(
            spec_ref=spec_ref,
            out_dir=out_dir,
            project_root=config.project_root,
        )
