"""Create a disposable Spec 012 project using the real CLI setup path."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "tests" / "fixtures" / "terminal-workflow"


def runtime_env() -> dict[str, str]:
    env = dict(os.environ)
    paths = [str(REPO / part / "src") for part in ("core", "cli", "mcp")]
    env["PYTHONPATH"] = os.pathsep.join([*paths, env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    return env


def cli(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "speccify_cli", *args, "--project", str(project)],
        cwd=project,
        env=runtime_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def create(project: Path) -> Path:
    project = project.resolve()
    # Never repurpose an existing project or an earlier acceptance run.
    project.mkdir(parents=True, exist_ok=False)
    shutil.copytree(SOURCE / "library", project / "skills")
    for args in (
        ("init",),
        ("add", "@qa/text-summary"),
        ("expand",),
    ):
        result = cli(project, *args)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
    for relative in (
        "AGENTS.md",
        "CLAUDE.md",
        ".agent/agent.md",
        ".agent/specs/001-summary/SPEC.md",
    ):
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            (SOURCE / "project" / relative).read_text(encoding="utf-8"), encoding="utf-8"
        )
    runtime = {
        "command": sys.executable,
        "cli_args": ["-m", "speccify_cli"],
        "mcp_args": ["-m", "speccify_mcp.cli", "--project", str(project)],
        "cwd": str(project),
        "env": {"PYTHONPATH": runtime_env()["PYTHONPATH"]},
    }
    (project / ".agent/runtime.md").write_text(
        "# Prepared runtime on this machine\n\n"
        "Use this interpreter and environment for CLI and real stdio MCP calls.\n"
        "The source paths provide the prepared runtime; only edit this disposable project.\n"
        "No installation or uv sync is needed. The interpreter includes the MCP client SDK.\n"
        "Compare the shared verify fields: ok, ready, platform, tools, notes, problems.\n\n"
        "```json\n" + json.dumps(runtime, indent=2, ensure_ascii=False) + "\n```\n",
        encoding="utf-8",
    )
    return project


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="New directory; must not exist")
    print(create(parser.parse_args().project))
