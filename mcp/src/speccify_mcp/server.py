"""MCP-Server-Konstruktion für Speccify.

In Phase 1c Step 1 ist der Server bewusst leer: keine Tools, keine
Resources, keine Prompts. Er dient als Skeleton, gegen das die
folgenden Steps (read-only Tools in Step 2, write-Tools in Step 3,
Resources/Prompts in Step 4) inkrementell aufbauen.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP

SERVER_NAME = "speccify-mcp"


@dataclass(frozen=True)
class ServerConfig:
    """Startup-Konfiguration des MCP-Servers.

    `project_root` ist der Projektpfad, gegen den alle stateless Tools
    in späteren Steps standardmäßig arbeiten (vgl. Phase-1c-Plan,
    Decision 3: Project-Root als Startup-Argument).
    """

    project_root: Path


def build_server(config: ServerConfig) -> FastMCP:
    """Baut eine `FastMCP`-Instanz ohne Tools/Resources/Prompts.

    Wir tragen `project_root` als Instructions-Metadatum mit, damit
    Clients beim Handshake sehen, gegen welches Projekt der Server
    läuft. Die eigentliche Verwendung passiert ab Step 2.
    """
    instructions = f"Speccify MCP server bound to project root: {config.project_root}"
    return FastMCP(name=SERVER_NAME, instructions=instructions)
