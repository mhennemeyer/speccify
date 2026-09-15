"""Spec 012: a real subprocess CLI/MCP roundtrip on a harmless local skill."""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path

from create_terminal_fixture import cli, create, runtime_env
from mcp.client.stdio import stdio_client
from speccify_core.expansion import Expansions
from speccify_core.tool_check import current_platform

from mcp import ClientSession, StdioServerParameters

CORRECT = """import json
import sys

text = json.load(sys.stdin)["text"]
print(json.dumps({"ok": True, "upper": text.upper(), "length": len(text)}))
"""


async def mcp_verify(project: Path) -> dict:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "speccify_mcp.cli", "--project", str(project)],
        env=runtime_env(),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("verify", {"offline": True})
            assert not result.isError, result
            return result.structuredContent or {}


def verify_parity(project: Path, *, ready: bool, state: str) -> None:
    result = cli(project, "verify", "--offline", "--json")
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    remote = asyncio.run(mcp_verify(project))
    for key in ("ok", "ready", "platform", "tools", "notes", "problems"):
        assert remote[key] == report[key], (key, report, remote)
    assert report["ok"] and report["ready"] is ready
    assert report["tools"] == [{"name": "summarize", "state": state}]


def test_setup_failed_tool_repair_and_real_stdio_parity(tmp_path: Path) -> None:
    project = create(tmp_path / "Unicode project ä")
    outside = tmp_path / "unrelated.txt"
    outside.write_text("unchanged", encoding="utf-8")
    for host in (".agents", ".claude"):
        assert (project / host / "skills" / "text-summary" / "SKILL.md").is_file()
    skill = (project / ".agent/skills/text-summary/SKILL.md").read_text(encoding="utf-8")
    assert "../../tools/summarize/TOOL.md" in skill
    assert "speccify.scope" not in skill
    verify_parity(project, ready=False, state="missing")

    tool = project / ".agent/tools/summarize"
    contract = (tool / "TOOL.md").read_bytes()
    implementation = tool / f"{current_platform()}.py"
    implementation.write_text(CORRECT.replace("text.upper()", "text.lower()"), encoding="utf-8")
    failed = cli(project, "tool", "check", "summarize", "--json")
    assert failed.returncode == 1, failed.stdout + failed.stderr
    report = json.loads(failed.stdout)
    assert not report["ok"]
    assert "$.upper" in failed.stdout
    verify_parity(project, ready=False, state="unverified")

    implementation.write_text(CORRECT, encoding="utf-8")
    passed = cli(project, "tool", "check", "summarize", "--json")
    assert passed.returncode == 0, passed.stdout + passed.stderr
    record_path = project / ".agent/speccify/expansions.yaml"
    assert Expansions.load(record_path).tools["summarize"].status(current_platform()) == "verified"
    record = record_path.read_bytes()
    verify_parity(project, ready=True, state="verified")
    assert record_path.read_bytes() == record, "verify must not mutate evidence"
    assert (tool / "TOOL.md").read_bytes() == contract
    assert outside.read_text(encoding="utf-8") == "unchanged"


def test_fixture_refuses_existing_project(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(FileExistsError):
        create(tmp_path)


def test_unavailable_library_does_not_mark_missing_tools_verified(tmp_path: Path) -> None:
    project = create(tmp_path / "missing-library")
    shutil.rmtree(project / "skills")
    for remove_lock in (False, True):
        if remove_lock:
            (project / "speccify.lock").unlink()
        result = cli(project, "verify", "--offline", "--json")
        assert result.returncode == 1
        report = json.loads(result.stdout)
        remote = asyncio.run(mcp_verify(project))
        assert not report["ok"] and not report["ready"]
        assert report["problems"]
        assert report["tools"] == remote["tools"] == [{"name": "summarize", "state": "missing"}]
