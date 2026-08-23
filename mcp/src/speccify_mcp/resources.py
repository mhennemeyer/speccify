"""MCP resources: the project's manifest and lockfile as readable documents."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mcp.server.fastmcp import FastMCP

    from .server import ServerConfig


def register_resources(server: FastMCP, config: ServerConfig) -> None:
    # Ressourcen haben keine Argumente — im Multi-Modus (kein gebundenes
    # Projekt) gibt es daher nichts, was sie zeigen könnten.
    if config.project_root is None:
        return

    @server.resource("speccify://manifest")
    def manifest() -> str:
        """The project's speccify.yaml."""
        assert config.project_root is not None
        path = config.project_root / "speccify.yaml"
        if not path.is_file():
            return "# No speccify.yaml in this project. Run `speccify init`."
        return path.read_text(encoding="utf-8")

    @server.resource("speccify://lockfile")
    def lockfile() -> str:
        """The project's speccify.lock."""
        assert config.project_root is not None
        path = config.project_root / "speccify.lock"
        if not path.is_file():
            return "# No speccify.lock yet. Run `speccify lock`."
        return path.read_text(encoding="utf-8")
