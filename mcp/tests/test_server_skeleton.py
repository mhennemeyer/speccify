"""Unit-Tests für das Phase-1c-Step-1-Server-Skeleton.

Wir prüfen:
- Der Server lässt sich mit einer `ServerConfig` bauen.
- `tools/list` antwortet leer (keine Tools in Step 1 registriert).
- Der CLI-Parser akzeptiert `--project`/`--log-level` und löst die
  Project-Root aus CLI > Env > CWD korrekt auf.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from speccify_mcp import SERVER_NAME, ServerConfig, build_server
from speccify_mcp.cli import build_parser, resolve_project_root


def test_build_server_returns_named_fastmcp_instance(tmp_path: Path) -> None:
    server = build_server(ServerConfig(project_root=tmp_path))
    assert server.name == SERVER_NAME


def test_tools_list_contains_step2_and_step3_tools(tmp_path: Path) -> None:
    # Step 2 (`resolve`/`lint`/`render`) + Step 3 (`lock`/`pull`/`verify`)
    # + `mock` (P2), `build` (P4) und `search` (P5). Resources/Prompts in Step 4.
    server = build_server(ServerConfig(project_root=tmp_path))
    tools = asyncio.run(server.list_tools())
    names = sorted(t.name for t in tools)
    assert names == [
        "build",
        "lint",
        "lock",
        "mock",
        "pull",
        "render",
        "resolve",
        "search",
        "verify",
    ]


def test_resources_list_contains_step4_resources(tmp_path: Path) -> None:
    # Step 4: zwei fixe Resources (manifest + lockfile) + ein Template
    # (`spec://...`). Templates landen in `list_resource_templates`,
    # nicht in `list_resources`.
    server = build_server(ServerConfig(project_root=tmp_path))
    resources = asyncio.run(server.list_resources())
    uris = sorted(str(r.uri) for r in resources)
    assert uris == ["speccify://lockfile", "speccify://manifest"]
    templates = asyncio.run(server.list_resource_templates())
    template_uris = [t.uriTemplate for t in templates]
    assert "spec://{scope}/{name}@{version}" in template_uris


def test_prompts_list_contains_add_spec(tmp_path: Path) -> None:
    server = build_server(ServerConfig(project_root=tmp_path))
    prompts = asyncio.run(server.list_prompts())
    names = sorted(p.name for p in prompts)
    assert names == ["add-spec"]


def test_parser_defaults() -> None:
    args = build_parser().parse_args([])
    assert args.project is None
    assert args.log_level in {"INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"}


def test_parser_accepts_project_and_log_level(tmp_path: Path) -> None:
    args = build_parser().parse_args(["--project", str(tmp_path), "--log-level", "DEBUG"])
    assert args.project == tmp_path
    assert args.log_level == "DEBUG"


def test_resolve_project_root_prefers_cli_argument(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPECCIFY_PROJECT_ROOT", str(tmp_path / "from-env"))
    cli_path = tmp_path / "from-cli"
    cli_path.mkdir()
    assert resolve_project_root(cli_path) == cli_path.resolve()


def test_resolve_project_root_falls_back_to_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "from-env"
    target.mkdir()
    monkeypatch.setenv("SPECCIFY_PROJECT_ROOT", str(target))
    assert resolve_project_root(None) == target.resolve()


def test_resolve_project_root_falls_back_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SPECCIFY_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    assert resolve_project_root(None) == tmp_path.resolve()
