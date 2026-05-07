"""Codegen-Pipeline für Speccify.

Phase 1a: deterministisches Stub-Target (`speccify_core.codegen.stub`) — Markdown
als Platzhalter. Phase 1b: Replay-Cache + `LlmClient`-Protokoll
(`speccify_core.codegen.replay`) als Fundament für den React-LLM-Adapter
(folgt in Step 4).
"""

from speccify_core.codegen.replay import (
    CacheKey,
    CacheMissError,
    LlmClient,
    ReplayCache,
    ReplayCacheClient,
)
from speccify_core.codegen.stub import (
    TEMPLATE_SET,
    TEMPLATE_VERSION,
    render,
    render_to_files,
)

__all__ = [
    "CacheKey",
    "CacheMissError",
    "LlmClient",
    "ReplayCache",
    "ReplayCacheClient",
    "TEMPLATE_SET",
    "TEMPLATE_VERSION",
    "render",
    "render_to_files",
]
