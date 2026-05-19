"""Render service — thin wrapper over `speccify_core.render_for_target`.

This module is intentionally framework-agnostic (no FastAPI imports) so the
cross-consistency test in Phase 1d Step 4 can call it the same way it calls
`speccify_cli.commands.pull.run_pull` and `speccify_mcp.tools.run_pull`.

Phase 1d MVP behaviour:
- Caller supplies raw YAML bytes + `spec_id` + `version` + `target`.
- We build a `Spec` directly from the bytes (no registry round-trip) so the
  playground can render edited YAML too — the cache key is derived from the
  raw bytes by `react_llm`, so edited YAML naturally results in a cache miss.
- Offline-only: `ReplayCacheClient(offline=True)`. Cache miss → `CacheMissError`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from speccify_core import (
    ReplayCache,
    ReplayCacheClient,
    Spec,
    Version,
    render_for_target,
)
from speccify_core.codegen import SUPPORTED_TARGETS


class UnknownTargetError(ValueError):
    """Caller asked for a target outside `SUPPORTED_TARGETS`."""


@dataclass(frozen=True)
class RenderServiceResult:
    """Same shape as the MCP `RenderResult.to_dict()` for downstream symmetry."""

    spec_id: str
    target: str
    files: dict[str, str]
    generator_pin: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "target": self.target,
            "files": dict(self.files),
            "generator_pin": (dict(self.generator_pin) if self.generator_pin is not None else None),
        }


def render_spec_from_yaml(
    spec_yaml: bytes,
    *,
    spec_id: str,
    version: str,
    target: str,
    cache_dir: Path,
) -> RenderServiceResult:
    """Render `spec_yaml` for `target` via the offline replay cache.

    Raises:
        UnknownTargetError: if `target` is not supported.
        speccify_core.CacheMissError: cache lookup missed (edited spec, missing
            recording — caller maps this to HTTP 422).
        ValueError: invalid `version` string (caller maps to 400).
    """
    if target not in SUPPORTED_TARGETS:
        raise UnknownTargetError(
            f"Unsupported target {target!r}. Supported: {', '.join(SUPPORTED_TARGETS)}."
        )

    parsed_version = Version.parse(version)
    spec = Spec(
        spec_id=spec_id,
        version=parsed_version,
        raw_bytes=spec_yaml,
        # In-memory spec — no on-disk path. react_llm only uses this for
        # error messages, never for I/O, so a synthetic path is fine.
        path=Path(f"<memory:{spec_id}@{version}>"),
    )

    cache = ReplayCache(cache_dir)
    llm_client = ReplayCacheClient(cache, offline=True)
    rendered = render_for_target(spec, target, llm_client=llm_client)

    files = {rel: data.decode("utf-8") for rel, data in sorted(rendered.files.items())}
    generator_pin: dict[str, Any] | None = None
    if rendered.cache_key is not None:
        generator_pin = {
            "kind": "llm",
            "model": rendered.cache_key.model,
            "prompt_version": rendered.cache_key.prompt_version,
            "cache_key": f"sha256:{rendered.cache_key.digest()}",
            "seed": rendered.cache_key.seed,
        }
    return RenderServiceResult(
        spec_id=spec_id,
        target=target,
        files=files,
        generator_pin=generator_pin,
    )
