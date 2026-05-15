"""Speccify MCP server package.

Public entry points:
- `speccify_mcp.cli.main`: argparse-driven entry point used by the
  `speccify-mcp` console script.
- `speccify_mcp.server.build_server`: returns a configured `FastMCP`
  instance; used by tests and (later) integration smoke checks.
"""

from .cli import main
from .server import SERVER_NAME, ServerConfig, build_server

__version__ = "0.0.0"
__all__ = ["main", "build_server", "ServerConfig", "SERVER_NAME", "__version__"]
