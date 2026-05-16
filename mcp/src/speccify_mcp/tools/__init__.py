"""Read-only MCP-Tools für Speccify (Phase 1c Step 2).

Jedes Tool ist ein dünner Adapter über `speccify_core` und gibt einen
JSON-serialisierbaren `dict` zurück (`structuredContent`-tauglich). Die
Module sind absichtlich frei von MCP-SDK-Imports, damit sie sich ohne
Subprocess testen lassen. Registriert werden sie zentral in
`speccify_mcp.server.build_server`.
"""

from .lint import LintResult, run_lint
from .render import RenderResult, run_render
from .resolve import ResolveResult, run_resolve

__all__ = [
    "LintResult",
    "RenderResult",
    "ResolveResult",
    "run_lint",
    "run_render",
    "run_resolve",
]
