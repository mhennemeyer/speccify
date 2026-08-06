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
    run_playbook_get,
    run_playbook_list,
    run_playbook_step,
    run_pull,
    run_search,
    run_verify,
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
        name="playbook_list",
        description=(
            "List the playbooks available in this project's library: id, version, "
            "title, summary, keywords, platforms and step count. Start here when "
            "you do not know what exists. Returns `{ok, playbooks}`."
        ),
    )
    def playbook_list(library_path: str | None = None) -> dict[str, Any]:
        return run_playbook_list(
            config.project_root,
            library_path=Path(library_path) if library_path else None,
        ).to_dict()

    @server.tool(
        name="playbook_get",
        description=(
            "Read a whole playbook: ordered steps, resolved sources (with the date "
            "they were retrieved), prerequisites, pitfalls and the list of bundled "
            "assets. `reference` is a playbook id ('@scope/name') or a git source "
            "('git+<url>[#<path>]'). Read this before starting the work — it is "
            "the knowledge you would otherwise have to research. Returns "
            "`{ok, playbook}`; unknown references report `code=not_found`."
        ),
    )
    def playbook_get(
        reference: str,
        library_path: str | None = None,
        offline: bool = False,
    ) -> dict[str, Any]:
        return run_playbook_get(
            config.project_root,
            reference=reference,
            library_path=Path(library_path) if library_path else None,
            offline=offline,
        ).to_dict()

    @server.tool(
        name="playbook_step",
        description=(
            "Read a single step of a playbook, with its sources resolved. Use this "
            "to work through a playbook one step at a time; each step carries a "
            "`verify` criterion telling you how to confirm it worked before moving "
            "on. A step may delegate to another playbook via `uses`. Returns "
            "`{ok, playbook: {step}}`."
        ),
    )
    def playbook_step(
        reference: str,
        step_id: str,
        library_path: str | None = None,
        offline: bool = False,
    ) -> dict[str, Any]:
        return run_playbook_step(
            config.project_root,
            reference=reference,
            step_id=step_id,
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
