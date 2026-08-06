"""MCP tools for Speccify.

Every tool is a thin adapter over `speccify-cli`, so the MCP and CLI paths
cannot drift. Tools return JSON-serialisable dicts and report failures as
structured results, never as MCP errors — an agent can act on a result, but an
exception just stops it.
"""

from .library import (
    AssetResult,
    CheckResult,
    LibraryResult,
    PlaybookResult,
    run_playbook_asset,
    run_playbook_check,
    run_playbook_get,
    run_playbook_list,
    run_playbook_step,
)
from .project import ProjectResult, run_lock, run_pull, run_verify
from .search import SearchResult, run_search

__all__ = [
    "AssetResult",
    "CheckResult",
    "LibraryResult",
    "PlaybookResult",
    "ProjectResult",
    "SearchResult",
    "run_lock",
    "run_playbook_asset",
    "run_playbook_check",
    "run_playbook_get",
    "run_playbook_list",
    "run_playbook_step",
    "run_pull",
    "run_search",
    "run_verify",
]
