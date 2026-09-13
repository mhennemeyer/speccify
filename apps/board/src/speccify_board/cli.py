"""`speccify-board`: serve one board for the repositories named in a YAML file."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(prog="speccify-board")
    parser.add_argument("--config", default=os.environ.get("BOARD_CONFIG", "board.yaml"))
    parser.add_argument("--data", default=os.environ.get("BOARD_DATA", "./board-data"))
    parser.add_argument("--host", default=os.environ.get("BOARD_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("BOARD_PORT", "8790")))
    args = parser.parse_args()

    import uvicorn

    from speccify_board.app import create_app
    from speccify_board.config import load_config

    config = load_config(Path(args.config))
    app = create_app(
        config,
        Path(args.data),
        password=os.environ.get("BOARD_PASSWORD") or None,
        mcp_token=os.environ.get("BOARD_MCP_TOKEN") or None,
    )
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
