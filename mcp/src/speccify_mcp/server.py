"""MCP-Server-Konstruktion für Speccify.

Phase 1c Step 1: Skeleton (leeres `tools/list`).
Phase 1c Step 2: Read-only Tools `resolve`, `lint`, `render` registriert.
Phase 1c Step 3: Write-Tools `lock`, `pull`, `verify` registriert
(dünne Adapter über `speccify_core`). Resources/Prompts folgen in Step 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .tools import run_lint, run_lock, run_pull, run_render, run_resolve, run_verify

SERVER_NAME = "speccify-mcp"


@dataclass(frozen=True)
class ServerConfig:
    """Startup-Konfiguration des MCP-Servers.

    `project_root` ist der Projektpfad, gegen den alle stateless Tools
    standardmäßig arbeiten (vgl. Phase-1c-Plan, Decision 3:
    Project-Root als Startup-Argument).
    """

    project_root: Path


def build_server(config: ServerConfig) -> FastMCP:
    """Baut eine `FastMCP`-Instanz mit registrierten Read-only Tools.

    Wir tragen `project_root` als Instructions-Metadatum mit, damit
    Clients beim Handshake sehen, gegen welches Projekt der Server
    läuft. Tools nehmen das Projekt-Root implizit aus `config`; ein
    optionales `manifest_path`-Argument erlaubt Override pro Call.
    """
    instructions = f"Speccify MCP server bound to project root: {config.project_root}"
    server = FastMCP(name=SERVER_NAME, instructions=instructions)
    _register_readonly_tools(server, config)
    _register_write_tools(server, config)
    return server


def _register_readonly_tools(server: FastMCP, config: ServerConfig) -> None:
    """Registriert die Phase-1c-Step-2-Tools über `FastMCP.tool()`.

    Alle Tools sind stateless und schreiben nichts auf Disk. Project-Root
    kommt aus der `ServerConfig`; `manifest_path`/`registry_path` etc.
    sind optionale Overrides für Sonderfälle (z.B. Tests).
    """

    @server.tool(
        name="resolve",
        description=(
            "Resolve the manifest's dependencies via MVS without writing "
            "a lockfile. Returns the resolved target and per-spec "
            "{spec_id, version, spec_sha256}."
        ),
    )
    def resolve(
        manifest_path: str | None = None,
        registry_path: str | None = None,
    ) -> dict[str, Any]:
        result = run_resolve(
            project_root=config.project_root,
            manifest_path=Path(manifest_path) if manifest_path else None,
            registry_path=Path(registry_path) if registry_path else None,
        )
        return result.to_dict()

    @server.tool(
        name="lint",
        description=(
            "Validate a single YAML spec against the Speccify spec schema "
            "v0. Project manifests (no `kind` field) are reported as "
            "`skipped=True`."
        ),
    )
    def lint(spec_path: str, schema_path: str | None = None) -> dict[str, Any]:
        result = run_lint(
            spec_path=Path(spec_path),
            schema_path=Path(schema_path) if schema_path else None,
        )
        return result.to_dict()

    @server.tool(
        name="render",
        description=(
            "Render a single spec from the project's lockfile for the "
            "lockfile's target. Does NOT write to disk; returns a "
            "{path: utf8-text} mapping and the generator pin for LLM "
            "targets. Offline by default (cache-miss is an error)."
        ),
    )
    def render(
        spec_id: str,
        target: str | None = None,
        offline: bool = True,
        cache_dir: str | None = None,
    ) -> dict[str, Any]:
        result = run_render(
            project_root=config.project_root,
            spec_id=spec_id,
            target=target,
            offline=offline,
            cache_dir=Path(cache_dir) if cache_dir else None,
        )
        return result.to_dict()


def _register_write_tools(server: FastMCP, config: ServerConfig) -> None:
    """Registriert die Phase-1c-Step-3-Tools über `FastMCP.tool()`.

    `lock` schreibt das Lockfile; `pull` schreibt Lockfile + Output-
    Dateien atomar; `verify` schreibt nichts und liefert eine
    Problemliste (leere Liste == grün).
    """

    @server.tool(
        name="lock",
        description=(
            "Resolve the manifest's dependencies via MVS and write "
            "`speccify.lock` to the project root. Mirrors `speccify lock`."
        ),
    )
    def lock(registry_path: str | None = None) -> dict[str, Any]:
        result = run_lock(
            project_root=config.project_root,
            registry_path=Path(registry_path) if registry_path else None,
        )
        return result.to_dict()

    @server.tool(
        name="pull",
        description=(
            "Render every locked spec for the lockfile's target and "
            "write the resulting files to `out_dir` (atomic), then "
            "update `generated_files_sha256` and the LLM generator pin "
            "in the lockfile. Offline by default (cache-miss is an "
            "error). Mirrors `speccify pull`."
        ),
    )
    def pull(
        out_dir: str,
        target: str | None = None,
        registry_path: str | None = None,
        offline: bool = True,
        cache_dir: str | None = None,
    ) -> dict[str, Any]:
        result = run_pull(
            project_root=config.project_root,
            out_dir=Path(out_dir),
            target=target,
            registry_path=Path(registry_path) if registry_path else None,
            offline=offline,
            cache_dir=Path(cache_dir) if cache_dir else None,
        )
        return result.to_dict()

    @server.tool(
        name="verify",
        description=(
            "Check that manifest, lockfile and rendered files on disk "
            "are still consistent. Returns `{ok: bool, problems: [str]}`. "
            "`ok=False` is reported in the structured result, not as an "
            "MCP error. Mirrors `speccify verify`."
        ),
    )
    def verify(
        out_dir: str,
        registry_path: str | None = None,
        offline: bool = True,
        cache_dir: str | None = None,
    ) -> dict[str, Any]:
        result = run_verify(
            project_root=config.project_root,
            out_dir=Path(out_dir),
            registry_path=Path(registry_path) if registry_path else None,
            offline=offline,
            cache_dir=Path(cache_dir) if cache_dir else None,
        )
        return result.to_dict()
