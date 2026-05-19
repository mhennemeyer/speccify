"""Entry point for `speccify-web-backend` — starts the FastAPI app via uvicorn.

The actual app factory lives in `speccify_web_backend.app:create_app` and will
be implemented in Step 1. This module only exists in Step 0 so the console
script declared in `pyproject.toml` resolves cleanly.
"""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(prog="speccify-web-backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Lazy import so the bare module load stays cheap; uvicorn pulls in a lot.
    import uvicorn

    from speccify_web_backend.app import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
