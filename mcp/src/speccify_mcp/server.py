"""Speccify MCP server: playbooks for coding agents, over stdio.

Every tool mirrors a CLI subcommand, so both paths cannot drift. Failures are
returned as structured results (`ok: false` plus a `code`), never as MCP
errors — an agent can react to a result, an exception just stops it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .tools import (
    run_lock,
    run_pull,
    run_search,
    run_skill_asset,
    run_skill_check,
    run_skill_get,
    run_skill_list,
    run_skill_propose,
    run_tool_get,
    run_verify,
    run_viewer_selection,
)

SERVER_NAME = "speccify-mcp"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServerConfig:
    """Where the server operates: the project whose manifest and library it reads."""

    project_root: Path


def build_server(config: ServerConfig) -> FastMCP:
    server = FastMCP(name=SERVER_NAME)

    @server.tool(
        name="skill_list",
        description=(
            "List the playbooks available in this project's library: id, version, "
            "title, summary, keywords, platforms and step count. Start here when "
            "you do not know what exists. Returns `{ok, playbooks}`."
        ),
    )
    def skill_list(library_path: str | None = None) -> dict[str, Any]:
        return run_skill_list(
            config.project_root,
            library_path=Path(library_path) if library_path else None,
        ).to_dict()

    @server.tool(
        name="skill_get",
        description=(
            "Read a whole playbook: ordered steps, resolved sources (with the date "
            "they were retrieved), prerequisites, pitfalls and the list of bundled "
            "assets. `reference` is a playbook id ('@scope/name') or a git source "
            "('git+<url>[#<path>]'). Read this before starting the work — it is "
            "the knowledge you would otherwise have to research. Returns "
            "`{ok, playbook}`; unknown references report `code=not_found`."
        ),
    )
    def skill_get(
        reference: str,
        library_path: str | None = None,
        offline: bool = False,
    ) -> dict[str, Any]:
        return run_skill_get(
            config.project_root,
            reference=reference,
            library_path=Path(library_path) if library_path else None,
            offline=offline,
        ).to_dict()

    @server.tool(
        name="skill_asset",
        description=(
            "Read a file that ships with a playbook — a script, a config, a "
            "template. `path` is bundle-relative (e.g. 'assets/verify.sh') and "
            "comes from a step's `assets` list or from `playbook_get`. Text is "
            "returned as-is, binary as base64. Returns `{ok, path, encoding, "
            "content}`."
        ),
    )
    def skill_asset(
        reference: str,
        path: str,
        library_path: str | None = None,
        offline: bool = False,
    ) -> dict[str, Any]:
        return run_skill_asset(
            config.project_root,
            reference=reference,
            path=path,
            library_path=Path(library_path) if library_path else None,
            offline=offline,
        ).to_dict()

    @server.tool(
        name="tool_get",
        description=(
            "Read one tool spec of a skill: input and output JSON Schema, effects, "
            "what must be installed, the examples that form the contract, and the "
            "files shipped beside it (a reference implementation, fixtures). Skills "
            "specify tools instead of shipping scripts, because scripts break on the "
            "next machine; read this, then write the implementation for the platform "
            "you are on and check it against the examples. `tool` is the name listed "
            "under `tools` in `skill_get`. Returns `{ok, tool}`; unknown names report "
            "`code=not_found` with what is available."
        ),
    )
    def tool_get(
        reference: str,
        tool: str,
        library_path: str | None = None,
        offline: bool = False,
    ) -> dict[str, Any]:
        return run_tool_get(
            config.project_root,
            reference=reference,
            tool=tool,
            library_path=Path(library_path) if library_path else None,
            offline=offline,
        ).to_dict()

    @server.tool(
        name="skill_check",
        description=(
            "Is this playbook still current? Checks structure and how long ago "
            "each source was retrieved; with `links=true` it also verifies that "
            "the source URLs still resolve (needs network). Worth running before "
            "you follow a playbook you have not used in a while — stale "
            "instructions are worse than none. Returns `{ok, findings}` where "
            "each finding has a level of `error` or `warning`."
        ),
    )
    def skill_check(
        reference: str,
        links: bool = False,
        library_path: str | None = None,
        offline: bool = False,
    ) -> dict[str, Any]:
        return run_skill_check(
            config.project_root,
            reference=reference,
            links=links,
            library_path=Path(library_path) if library_path else None,
            offline=offline,
        ).to_dict()

    @server.tool(
        name="search",
        description=(
            "Find playbooks in discovery indexes (git repositories or local "
            "directories with one file per playbook repository). Sources: the "
            "`index_sources` argument > `SPECCIFY_INDEX` > `<project>/index`. Each "
            "hit carries the git source to put into a manifest. Mirrors "
            "`speccify search`."
        ),
    )
    def search(
        query: str = "",
        index_sources: list[str] | None = None,
        offline: bool = False,
    ) -> dict[str, Any]:
        return run_search(
            project_root=config.project_root,
            query=query,
            index_sources=index_sources,
            offline=offline,
        ).to_dict()

    @server.tool(
        name="viewer_selection",
        description=(
            "What the user currently has selected in the Speccify viewer — the "
            "playbook, and the step, source or asset they clicked, already "
            "resolved. Call this **first** when the user asks about 'this step' "
            "or 'why is that necessary' while looking at the viewer; it is the "
            "context they did not restate. Returns `{ok, selection}`; an empty "
            "selection means nothing is open."
        ),
    )
    def viewer_selection() -> dict[str, Any]:
        return run_viewer_selection().to_dict()

    @server.tool(
        name="skill_propose",
        description=(
            "Propose a changed skill. Pass the **complete** new "
            "`SKILL.md`; it is validated and then shown to the user in the "
            "viewer as a diff. Nothing is written until they apply it — this is "
            "how playbooks are edited, there is no edit mode. Returns "
            "`{ok, code, message}`; invalid YAML or a broken playbook comes "
            "back as `code=invalid_skill` with the reason."
        ),
    )
    def skill_propose(
        source: str,
        skill_markdown: str,
        rationale: str = "",
    ) -> dict[str, Any]:
        return run_skill_propose(
            source=source, skill_markdown=skill_markdown, rationale=rationale
        ).to_dict()

    @server.tool(
        name="lock",
        description=(
            "Resolve the project manifest and write speccify.lock, pinning every "
            "playbook bundle by hash and — for git sources — by commit. Mirrors "
            "`speccify lock`. Returns `{ok, entries}`."
        ),
    )
    def lock(library_path: str | None = None) -> dict[str, Any]:
        return run_lock(
            config.project_root,
            library_path=Path(library_path) if library_path else None,
        ).to_dict()

    @server.tool(
        name="pull",
        description=(
            "Materialise the locked playbook bundles (including assets) into a "
            "directory, verifying each bundle hash against the lockfile. Useful "
            "when you want the files on disk rather than through this server. "
            "Mirrors `speccify pull`."
        ),
    )
    def pull(
        out_dir: str = "./speccify_playbooks",
        library_path: str | None = None,
        offline: bool = False,
    ) -> dict[str, Any]:
        return run_pull(
            config.project_root,
            out_dir=Path(out_dir),
            library_path=Path(library_path) if library_path else None,
            offline=offline,
        ).to_dict()

    @server.tool(
        name="verify",
        description=(
            "Check that the lockfile still matches the manifest and the actual "
            "bundles — version drift, bundle-hash drift and moved tags. Drift is a "
            "structured result (`{ok: false, problems}`), not an error. Mirrors "
            "`speccify verify`."
        ),
    )
    def verify(library_path: str | None = None, offline: bool = False) -> dict[str, Any]:
        return run_verify(
            config.project_root,
            library_path=Path(library_path) if library_path else None,
            offline=offline,
        ).to_dict()

    _register_resources(server, config)
    return server


def _register_resources(server: FastMCP, config: ServerConfig) -> None:
    from .resources import register_resources

    register_resources(server, config)
