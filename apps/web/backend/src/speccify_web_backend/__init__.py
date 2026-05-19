"""Speccify web playground backend (FastAPI).

Thin adapter over speccify-core that exposes the same render pipeline used by
the CLI and MCP server. Offline-only in Phase 1d: render calls go through the
replay cache, never against a live LLM.
"""

__version__ = "0.0.0"
