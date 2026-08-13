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
    run_skill_asset,
    run_skill_check,
    run_skill_get,
    run_skill_list,
)
from .project import ProjectResult, run_lock, run_pull, run_verify
from .search import SearchResult, run_search
from .viewer import (
    ProposalResult,
    ViewerResult,
    run_skill_propose,
    run_viewer_selection,
)

__all__ = [
    "AssetResult",
    "CheckResult",
    "LibraryResult",
    "PlaybookResult",
    "ProjectResult",
    "ProposalResult",
    "SearchResult",
    "ViewerResult",
    "run_lock",
    "run_skill_asset",
    "run_skill_check",
    "run_skill_get",
    "run_skill_list",
    "run_skill_propose",
    "run_pull",
    "run_search",
    "run_verify",
    "run_viewer_selection",
]
