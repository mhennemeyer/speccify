"""CLI-Entry-Point für `speccify-mcp`.

Startet den Speccify-MCP-Server auf `stdio`. Wir halten den Entry-Point
bewusst klein: Argumente parsen → Logging konfigurieren →
`server.run(...)` aufrufen. Alles weitere lebt in `server.py`.
"""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence
from pathlib import Path

from .server import ServerConfig, build_server

_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def build_parser() -> argparse.ArgumentParser:
    """Erzeugt den `argparse`-Parser für `speccify-mcp`."""
    parser = argparse.ArgumentParser(
        prog="speccify-mcp",
        description=(
            "Speccify MCP server — exposes speccify_core (resolve/lock/"
            "render/pull/verify/lint) to coding agents over stdio."
        ),
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=None,
        help=(
            "Project root the server is bound to. Defaults to "
            "$SPECCIFY_PROJECT_ROOT or the current working directory."
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=_LOG_LEVELS,
        default=os.environ.get("SPECCIFY_LOG_LEVEL", "INFO"),
        help="Log level for stderr logging (default: INFO).",
    )
    return parser


def resolve_project_root(raw: Path | None) -> Path:
    """Findet die Project-Root nach CLI > Env > CWD."""
    if raw is not None:
        return raw.expanduser().resolve()
    env_value = os.environ.get("SPECCIFY_PROJECT_ROOT")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return Path.cwd().resolve()


def configure_logging(level: str) -> None:
    """Konfiguriert Logging auf stderr (MCP-konform).

    stdout ist für MCP-stdio-Frames reserviert; Logs müssen nach stderr.
    `logging.basicConfig` ohne `stream`-Override schreibt per Default
    nach stderr.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Entry-Point für `speccify-mcp`. Gibt Exit-Code zurück."""
    args = build_parser().parse_args(argv)
    configure_logging(args.log_level)

    project_root = resolve_project_root(args.project)
    logging.getLogger("speccify_mcp").info(
        "starting speccify-mcp on stdio (project_root=%s)", project_root
    )

    server = build_server(ServerConfig(project_root=project_root))
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
