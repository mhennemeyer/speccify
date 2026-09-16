"""The board as an MCP server (Spec 033): the same registry the pages use,
exposed as tools and resources over Streamable HTTP under `/mcp`, so itsdcloud
(or any MCP client) can read the board and — if allowed — move stations and
tick tasks. Tools mirror the HTTP API; there is no second logic."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from speccify_core.board import BoardSpec, summarize

from speccify_board.config import BoardConfig
from speccify_board.registry import Registry
from speccify_board.sources import SourceError

SERVER_NAME = "speccify-board"


def _spec_row(spec: BoardSpec) -> dict[str, Any]:
    row = spec.to_dict()
    row["flags"] = [
        flag
        for flag, present in (
            ("ready", spec.ready),
            ("needs_human", spec.needs_human),
            ("question", bool(spec.open_question)),
            ("idea", spec.station == "Backlog" and spec.order is None),
        )
        if present
    ]
    row["owner_name"] = spec.owner_name
    return row


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "code": code, "message": message}


def build_mcp(registry: Registry, config: BoardConfig) -> FastMCP:
    server = FastMCP(
        name=SERVER_NAME,
        instructions=(
            f"Spec board '{config.title}': the Speccify spec registers of "
            f"{', '.join(config.names) or 'no'} repositories. Specs move through "
            "Backlog → Doing → Done; `owner` and `branch` say who works on what and "
            "where. Read with board_summary / list_specs / who_works_on_what; "
            "move_station and toggle_task write into the register (a Git commit)."
        ),
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
    )

    def live(name: str | None = None) -> list[BoardSpec]:
        return [spec for spec in registry.specs(name) if not spec.archived]

    @server.tool(
        name="board_summary",
        description=(
            "Totals for the whole board and per repository: specs per station, tasks "
            "done/total, ready for acceptance, open questions, agent runs in the last "
            "30 days, and each repository's state (commit, last refresh, error)."
        ),
    )
    def board_summary() -> dict[str, Any]:
        return {
            "ok": True,
            "title": config.title,
            "summary": summarize(live()),
            "repos": registry.status(),
        }

    @server.tool(
        name="list_repos",
        description="The repositories on this board with kind (git/path), branch, commit, last refresh and error.",
    )
    def list_repos() -> dict[str, Any]:
        return {"ok": True, "repos": registry.status()}

    @server.tool(
        name="list_specs",
        description=(
            "Specs on the board (archive excluded). Filter by `repo`, `station` "
            "(Backlog|Doing|Done), `owner` (name or e-mail fragment) or a free-text "
            "`query` over number, title, id, owner and branch. Each row has number, "
            "title, station, owner, branch, tasks_done/tasks_total, flags and last_activity."
        ),
    )
    def list_specs(
        repo: str | None = None,
        station: str | None = None,
        owner: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        if repo is not None and repo.split("/", 1)[0] not in registry.sources:
            return _error("unknown_repo", f"Unbekanntes Repo: {repo}")
        rows = []
        needle = (query or "").strip().lower()
        who = (owner or "").strip().lower()
        for spec in live():
            if repo and (spec.repo or "") != repo and not (spec.repo or "").startswith(repo + "/"):
                continue
            if station and spec.station != station:
                continue
            if who and who not in (spec.owner or "").lower():
                continue
            haystack = " ".join(
                filter(
                    None,
                    [
                        str(spec.number or ""),
                        spec.title,
                        spec.id,
                        spec.owner or "",
                        spec.branch or "",
                    ],
                )
            ).lower()
            if needle and needle not in haystack:
                continue
            rows.append(_spec_row(spec))
        rows.sort(
            key=lambda row: (
                row["station"],
                row["order"] if row["order"] is not None else 10**9,
                row["id"],
            )
        )
        return {"ok": True, "count": len(rows), "specs": rows}

    @server.tool(
        name="get_spec",
        description=(
            "One spec in full: front matter fields, tasks with done flags, the last "
            "history events (newest first) and the Markdown body."
        ),
    )
    def get_spec(repo: str, spec_id: str, history_limit: int = 20) -> dict[str, Any]:
        spec = next(
            (s for s in registry.specs() if s.id == spec_id and s.repo == repo),
            None,
        )
        if spec is None:
            return _error("not_found", f"Keine Spec {spec_id} in {repo}")
        source = registry.sources.get(repo.split("/", 1)[0])
        body = ""
        if source is not None:
            try:
                _label, candidate = source._folder_for(spec_id, repo)
                body = candidate.read_text(encoding="utf-8", errors="replace")
            except SourceError:
                body = ""
        row = _spec_row(spec)
        row["tasks"] = [
            {"index": i, "text": t.text, "done": t.done} for i, t in enumerate(spec.tasks)
        ]
        row["history"] = [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "actor": e.actor,
                "summary": e.summary,
            }
            for e in reversed(spec.history[-history_limit:])
        ]
        row["body"] = body
        return {"ok": True, "spec": row}

    @server.tool(
        name="who_works_on_what",
        description="Doing specs grouped by owner (person), each with branch and task progress; specs without owner are listed under 'unassigned'.",
    )
    def who_works_on_what() -> dict[str, Any]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for spec in live():
            if spec.station != "Doing":
                continue
            key = spec.owner_name or "unassigned"
            groups.setdefault(key, []).append(
                {
                    "repo": spec.repo,
                    "id": spec.id,
                    "number": spec.number,
                    "title": spec.title,
                    "branch": spec.branch,
                    "tasks_done": spec.tasks_done,
                    "tasks_total": spec.tasks_total,
                    "ready": spec.ready,
                }
            )
        return {
            "ok": True,
            "people": [{"person": name, "specs": specs} for name, specs in sorted(groups.items())],
        }

    def _source(repo: str):
        return registry.sources.get(repo.split("/", 1)[0])

    @server.tool(
        name="move_station",
        description="Move a spec to Backlog, Doing or Done. Rewrites only the station line, logs a history event and commits/pushes to the register branch. Returns the commit.",
    )
    def move_station(
        repo: str, spec_id: str, station: str, expected_revision: str | None = None
    ) -> dict[str, Any]:
        source = _source(repo)
        if source is None:
            return _error("unknown_repo", f"Unbekanntes Repo: {repo}")
        try:
            commit = source.move_station(
                spec_id, station, source=repo, expected_revision=expected_revision
            )
        except SourceError as exc:
            return _error("rejected", str(exc))
        source.refresh()
        return {"ok": True, "commit": commit}

    @server.tool(
        name="toggle_task",
        description="Tick (done=true) or untick one task by its 0-based index from get_spec. Commits/pushes to the register branch. Returns the commit.",
    )
    def toggle_task(
        repo: str, spec_id: str, index: int, done: bool, expected_revision: str | None = None
    ) -> dict[str, Any]:
        source = _source(repo)
        if source is None:
            return _error("unknown_repo", f"Unbekanntes Repo: {repo}")
        try:
            commit = source.toggle_task(
                spec_id, index, done, source=repo, expected_revision=expected_revision
            )
        except SourceError as exc:
            return _error("rejected", str(exc))
        source.refresh()
        return {"ok": True, "commit": commit}

    @server.tool(name="refresh", description="Fetch every repository now and return their state.")
    def refresh() -> dict[str, Any]:
        registry.refresh_all()
        return {"ok": True, "repos": registry.status()}

    @server.resource("board://summary")
    def summary_resource() -> str:
        """Board totals as JSON."""
        return json.dumps(
            {"title": config.title, "summary": summarize(live()), "repos": registry.status()},
            ensure_ascii=False,
        )

    @server.resource("board://{repo}/{spec_id}")
    def spec_resource(repo: str, spec_id: str) -> str:
        """A spec's SPEC.md as Markdown."""
        result = get_spec(repo, spec_id)
        return (
            result.get("spec", {}).get("body", "")
            if result.get("ok")
            else f"# {result.get('message')}"
        )

    return server
