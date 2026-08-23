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
    run_add,
    run_expand,
    run_lock,
    run_pull,
    run_search,
    run_skill_asset,
    run_skill_check,
    run_skill_get,
    run_skill_list,
    run_skill_propose,
    run_source_list,
    run_tool_check,
    run_tool_get,
    run_verify,
    run_viewer_selection,
)

SERVER_NAME = "speccify-mcp"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServerConfig:
    """Where the server operates.

    `project_root` gesetzt = **gebunden** (ein Projekt, wie bisher über
    stdio). `None` = **multi**: jeder projektbezogene Aufruf bringt `project`
    mit — so kann ein Server hinter einem Port mehrere Projektfenster einer
    App bedienen (dasselbe Muster wie beim `speccify-exec-mcp`).
    """

    project_root: Path | None = None

    @property
    def bound(self) -> bool:
        return self.project_root is not None


_PROJECT_ARG_DOC = (
    " `project`: absolute project root; required when the server runs unbound "
    "(multi mode), ignored when it is bound to one project."
)


def _resolve_root(config: ServerConfig, project: str | None) -> Path | dict[str, Any]:
    """Projektwurzel für einen Aufruf — oder ein strukturierter Fehler."""
    if config.project_root is not None:
        return config.project_root
    if not project:
        return {
            "ok": False,
            "code": "project_required",
            "message": "Server runs unbound: pass `project` (absolute project root).",
        }
    root = Path(project).expanduser()
    if not root.is_absolute() or not root.is_dir():
        return {
            "ok": False,
            "code": "project_not_found",
            "message": f"`project` must be an existing absolute directory, got '{project}'.",
        }
    return root.resolve()


def build_server(config: ServerConfig, **fastmcp_settings: Any) -> FastMCP:
    """Server mit allen Tools; `fastmcp_settings` (host, port, …) gehen an FastMCP."""
    server = FastMCP(name=SERVER_NAME, **fastmcp_settings)

    @server.tool(
        name="skill_list",
        description=(
            "List the playbooks available in this project's library: id, version, "
            "title, summary, keywords, platforms and step count. Start here when "
            "you do not know what exists. Returns `{ok, playbooks}`."
        ),
    )
    def skill_list(library_path: str | None = None, project: str | None = None) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_skill_list(
            root,
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
        project: str | None = None,
    ) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_skill_get(
            root,
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
        project: str | None = None,
    ) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_skill_asset(
            root,
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
        project: str | None = None,
    ) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_tool_get(
            root,
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
        project: str | None = None,
    ) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_skill_check(
            root,
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
        project: str | None = None,
    ) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_search(
            project_root=root,
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
    def lock(library_path: str | None = None, project: str | None = None) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_lock(
            root,
            library_path=Path(library_path) if library_path else None,
        ).to_dict()

    @server.tool(
        name="pull",
        description=(
            "Materialise the locked skill bundles untouched (upstream form, with "
            "assets and tool specs) into a directory, verifying each bundle hash "
            "against the lockfile. For diffing or reading upstream as-is; what the "
            "agent should use comes from `expand`. Mirrors `speccify pull`."
        ),
    )
    def pull(
        out_dir: str = "./.agent/speccify/cache",
        library_path: str | None = None,
        offline: bool = False,
        project: str | None = None,
    ) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_pull(
            root,
            out_dir=Path(out_dir),
            library_path=Path(library_path) if library_path else None,
            offline=offline,
        ).to_dict()

    @server.tool(
        name="expand",
        description=(
            "Turn the locked skills into normal, project-specific skills under "
            ".agent/skills/ (what this agent reads via .claude/skills) and put "
            "their tool specs under .agent/tools/. Resolves what each skill builds "
            "on, strips Speccify metadata, keeps the `## In this project` section "
            "across re-runs. Returns `{ok, platform, skills, tools_to_implement}` "
            "— the to-do list: placeholders to fill in per skill, and tools that "
            "need an implementation for this platform (`<platform>.<ext>` beside "
            "the TOOL.md, JSON in on stdin, JSON out on stdout). Mirrors "
            "`speccify expand`; omit `references` to expand every manifest dependency."
        ),
    )
    def expand(
        references: list[str] | None = None,
        library_path: str | None = None,
        offline: bool = False,
        platform: str | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_expand(
            root,
            references=references,
            library_path=Path(library_path) if library_path else None,
            offline=offline,
            platform=platform,
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
    def verify(
        library_path: str | None = None, offline: bool = False, project: str | None = None
    ) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_verify(
            root,
            library_path=Path(library_path) if library_path else None,
            offline=offline,
        ).to_dict()

    @server.tool(
        name="source_list",
        description=(
            "List every skill a git repository offers, read from its tags "
            "(`<path>/v<version>`): id to put into `add`, path, versions, latest, "
            "name and description from the newest SKILL.md. This is how an app "
            '"connects a source" — no manifest change, nothing written. '
            "`source` is 'git+<url>'. Returns `{ok, source, skills}`."
        ),
    )
    def source_list(source: str, offline: bool = False) -> dict[str, Any]:
        return run_source_list(source, offline=offline).to_dict()

    @server.tool(
        name="add",
        description=(
            "Add a skill dependency to the project manifest and re-lock — the "
            "import step after `source_list`. `reference` is a skill id "
            "('@scope/name'), a git source ('git+<url>#<path>'), optionally with "
            "'@<version>'; without a version the newest one is taken and written "
            "as a caret range. Mirrors `speccify add`. Returns `{ok, reference, "
            "range}`; follow with `expand`." + _PROJECT_ARG_DOC
        ),
    )
    def add(
        reference: str,
        library_path: str | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_add(
            root,
            reference=reference,
            library_path=Path(library_path) if library_path else None,
        ).to_dict()

    @server.tool(
        name="tool_check",
        description=(
            "Run each tool spec's `## Examples` against the implementation for this "
            "platform under .agent/tools/<name>/<platform>.<ext> — JSON in on stdin, "
            "JSON out on stdout. A tool whose examples all pass is recorded as "
            "`verified` in .agent/speccify/expansions.yaml; a failing one goes back "
            "to `implemented`. Returns `{ok, platform, tools: [{name, status, cases}]}` "
            "with the expected and actual output per failing example. This is the "
            "mechanical half of Evaluate; mirrors `speccify tool check`. Omit `names` "
            "to check every tool."
        ),
    )
    def tool_check(
        names: list[str] | None = None,
        platform: str | None = None,
        timeout: float | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        root = _resolve_root(config, project)
        if isinstance(root, dict):
            return root
        return run_tool_check(root, names=names, platform=platform, timeout=timeout).to_dict()

    _register_resources(server, config)
    return server


def _register_resources(server: FastMCP, config: ServerConfig) -> None:
    from .resources import register_resources

    register_resources(server, config)
