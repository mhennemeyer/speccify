"""MCP-Tools für Speccify (Phase 1c Steps 2 + 3).

Jedes Tool ist ein dünner Adapter über `speccify_core` und gibt einen
JSON-serialisierbaren `dict` zurück (`structuredContent`-tauglich). Die
Module sind absichtlich frei von MCP-SDK-Imports, damit sie sich ohne
Subprocess testen lassen. Registriert werden sie zentral in
`speccify_mcp.server.build_server`.

- Step 2 (read-only): `resolve`, `lint`, `render`.
- Step 3 (write): `lock`, `pull`, `verify`.
- P2/P4: `mock` (Mock-Closure), `build` (Projekt aus `kind: app`).
"""

from .build import BuildResult, run_build
from .lint import LintResult, run_lint
from .lock import LockResult, run_lock
from .mock import MockResult, run_mock
from .pull import PullResult, run_pull
from .render import RenderResult, run_render
from .resolve import ResolveResult, run_resolve
from .search import SearchResult, run_search
from .verify import VerifyResult, run_verify

__all__ = [
    "BuildResult",
    "LintResult",
    "LockResult",
    "MockResult",
    "PullResult",
    "RenderResult",
    "ResolveResult",
    "SearchResult",
    "VerifyResult",
    "run_build",
    "run_lint",
    "run_lock",
    "run_mock",
    "run_pull",
    "run_render",
    "run_resolve",
    "run_search",
    "run_verify",
]
