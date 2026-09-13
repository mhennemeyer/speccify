"""The board's MCP server (Spec 033), exercised with the real MCP client over
Streamable HTTP against a uvicorn thread."""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn
from mcp.client.streamable_http import streamablehttp_client
from speccify_board.app import create_app
from speccify_board.config import parse_config
from test_board_service import SPEC_A, SPEC_B, git, make_register

from mcp import ClientSession


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def served(tmp_path: Path):
    app_bare = make_register(tmp_path / "remotes", "app", {"001-login": SPEC_A})
    portal_bare = make_register(tmp_path / "remotes", "portal", {"002-suche": SPEC_B})
    config = parse_config(
        f"title: Team Alpha\nauthor: Web-Board <board@example.invalid>\nrepos:\n"
        f"  - name: app\n    url: {app_bare}\n  - name: portal\n    url: {portal_bare}\n"
    )
    app = create_app(config, tmp_path / "data", mcp_token="t0ken", background=False)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 15
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started
    yield {"url": f"http://127.0.0.1:{port}/mcp", "app": app_bare}
    server.should_exit = True
    thread.join(timeout=10)


def _call(url: str, token: str | None, name: str, args: dict[str, Any] | None = None) -> Any:
    async def run() -> Any:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        async with streamablehttp_client(url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                if name == "tools/list":
                    return sorted(tool.name for tool in (await session.list_tools()).tools)
                if name == "resources/read":
                    result = await session.read_resource(args["uri"])  # type: ignore[index]
                    return result.contents[0].text  # type: ignore[union-attr]
                result = await session.call_tool(name, args or {})
                assert result.content and result.content[0].type == "text"
                return json.loads(result.content[0].text)  # type: ignore[union-attr]

    return asyncio.run(run())


def test_handshake_tools_and_reads(served: dict[str, Any]) -> None:
    url = served["url"]
    assert _call(url, "t0ken", "tools/list") == [
        "board_summary",
        "get_spec",
        "list_repos",
        "list_specs",
        "move_station",
        "refresh",
        "toggle_task",
        "who_works_on_what",
    ]
    summary = _call(url, "t0ken", "board_summary")
    assert summary["ok"] and summary["summary"]["stations"] == {"Backlog": 1, "Doing": 1, "Done": 0}
    assert {r["name"] for r in summary["repos"]} == {"app", "portal"}
    doing = _call(url, "t0ken", "list_specs", {"station": "Doing"})
    assert doing["count"] == 1 and doing["specs"][0]["title"] == "App-Login"
    assert doing["specs"][0]["owner_name"] == "Anna" and doing["specs"][0]["repo"] == "app"
    assert _call(url, "t0ken", "list_specs", {"repo": "portal"})["specs"][0]["id"] == "002-suche"
    assert _call(url, "t0ken", "list_specs", {"repo": "nope"})["code"] == "unknown_repo"
    assert _call(url, "t0ken", "list_specs", {"query": "suche"})["count"] == 1
    assert _call(url, "t0ken", "list_specs", {"owner": "anna@"})["count"] == 1
    spec = _call(url, "t0ken", "get_spec", {"repo": "app", "spec_id": "001-login"})["spec"]
    assert spec["tasks"] == [
        {"index": 0, "text": "eins", "done": True},
        {"index": 1, "text": "zwei", "done": False},
    ]
    assert spec["body"].startswith("---\nstation: Doing")
    assert _call(url, "t0ken", "get_spec", {"repo": "app", "spec_id": "x"})["code"] == "not_found"
    people = _call(url, "t0ken", "who_works_on_what")["people"]
    assert people == [
        {
            "person": "Anna",
            "specs": [
                {
                    "repo": "app",
                    "id": "001-login",
                    "number": 1,
                    "title": "App-Login",
                    "branch": None,
                    "tasks_done": 1,
                    "tasks_total": 2,
                    "ready": False,
                }
            ],
        }
    ]
    assert "Team Alpha" in _call(url, "t0ken", "resources/read", {"uri": "board://summary"})
    assert _call(url, "t0ken", "resources/read", {"uri": "board://app/001-login"}).startswith("---")


def test_writes_commit_to_the_register(served: dict[str, Any], tmp_path: Path) -> None:
    url = served["url"]
    moved = _call(
        url, "t0ken", "move_station", {"repo": "app", "spec_id": "001-login", "station": "Done"}
    )
    assert moved["ok"] and moved["commit"]
    ticked = _call(
        url,
        "t0ken",
        "toggle_task",
        {"repo": "app", "spec_id": "001-login", "index": 1, "done": True},
    )
    assert ticked["ok"]
    check = tmp_path / "check"
    git(tmp_path, "clone", "-q", "--branch", "specs", str(served["app"]), "check")
    text = (check / "001-login" / "SPEC.md").read_text(encoding="utf-8")
    assert "station: Done" in text and "- [x] zwei" in text
    assert git(check, "log", "--format=%s", "-2").splitlines() == [
        "spec(001-login): Task 2 erledigt (Web-Board)",
        "spec(001-login): Doing -> Done (Web-Board)",
    ]
    assert (
        _call(url, "t0ken", "move_station", {"repo": "app", "spec_id": "nope", "station": "Done"})[
            "code"
        ]
        == "rejected"
    )
    assert (
        _call(
            url, "t0ken", "move_station", {"repo": "zzz", "spec_id": "001-login", "station": "Done"}
        )["code"]
        == "unknown_repo"
    )
    assert _call(url, "t0ken", "refresh")["ok"]


def test_bearer_token_guards_mcp(served: dict[str, Any]) -> None:
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "probe", "version": "0"},
        },
    }
    headers = {"accept": "application/json, text/event-stream"}
    assert httpx.post(served["url"], json=init, headers=headers).status_code == 401
    wrong = {**headers, "authorization": "Bearer wrong"}
    assert httpx.post(served["url"], json=init, headers=wrong).status_code == 401
    right = {**headers, "authorization": "Bearer t0ken"}
    response = httpx.post(served["url"], json=init, headers=right)
    assert response.status_code == 200, response.text
    assert response.json()["result"]["serverInfo"]["name"] == "speccify-board"
    assert not response.history, "no redirect on POST /mcp"
