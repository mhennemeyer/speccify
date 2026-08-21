"""Smoke test for the `speccify-mcp` stdio server.

Starts the server as a subprocess, speaks MCP over stdio with the official
client and checks the three things that matter: the tool list, reading a
playbook, and reading the manifest resource. Run standalone or via
`mcp/tests/test_stdio_smoke.py`.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "skills"
REFERENCE = "@speccify/macos-notarize-tauri"

EXPECTED_TOOLS = {
    "expand",
    "lock",
    "skill_propose",
    "skill_asset",
    "skill_check",
    "skill_get",
    "skill_list",
    "tool_get",
    "pull",
    "search",
    "verify",
    "viewer_selection",
}


def _prepare_project(tmp: Path) -> Path:
    """A throwaway project with its own copy of the skill library."""
    shutil.copytree(SKILLS, tmp / "skills")
    (tmp / "speccify.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    return tmp


async def _run(project: Path) -> None:
    # Inherit PYTHONPATH: the workspace packages are importable that way even
    # when the venv has no editable install (a recurring macOS quirk).
    import os

    env = dict(os.environ)
    src_paths = [str(REPO_ROOT / part / "src") for part in ("core", "cli", "mcp")]
    env["PYTHONPATH"] = os.pathsep.join([*src_paths, env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "speccify_mcp.cli", "--project", str(project)],
        env=env,
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == EXPECTED_TOOLS, (
                f"tools/list mismatch: got {sorted(names)}, expected {sorted(EXPECTED_TOOLS)}"
            )
            print(f"[ok] tools/list = {sorted(names)}", file=sys.stderr)

            result = await session.call_tool("skill_get", {"reference": REFERENCE})
            payload = result.structuredContent or {}
            assert payload.get("ok"), f"skill_get failed: {payload}"
            skill = payload["playbook"]
            assert len(skill["steps"]) == 5, f"expected 5 steps, got {len(skill['steps'])}"
            # A composed skill: it names what it builds on.
            assert skill["uses"], "this skill should build on a child skill"
            assert skill["body"].strip(), "the body is what the agent would follow"
            print(
                f"[ok] skill_get -> {len(skill['steps'])} steps, builds on {skill['uses']}",
                file=sys.stderr,
            )

            manifest = await session.read_resource("speccify://manifest")
            assert "schema_version" in manifest.contents[0].text
            print("[ok] resources/read speccify://manifest", file=sys.stderr)


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        project = _prepare_project(Path(raw))
        try:
            asyncio.run(_run(project))
        except AssertionError as exc:
            print(f"[fail] {exc}", file=sys.stderr)
            return 1
        except Exception as exc:  # noqa: BLE001 - smoke test reports and exits
            print(f"[fail] unexpected: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
    print("[ok] speccify-mcp stdio smoke passed", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
