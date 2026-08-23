"""`speccify tool check`: do the implementations under `.agent/tools/` honour their specs?

This is the mechanical half of Evaluate. For every tool (or the named ones) it
runs the examples of `TOOL.md` against `<platform>.<ext>` and records the
result in `.agent/speccify/expansions.yaml`: all examples pass → `verified`
(with the date); anything else → back to `implemented`. `verify` reads that
status, so a tool that has been checked stops showing up as "not yet checked".

Nothing here judges whether the *skill* did the right thing — that is the
agent's part of Evaluate, described in the Speccify skill.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import typer
from speccify_core.expansion import (
    AGENT_DIR,
    IMPLEMENTED,
    VERIFIED,
    Expansions,
    ToolRecord,
    current_platform,
    sha256_text,
)
from speccify_core.tool import TOOL_FILENAME, TOOLS_DIR
from speccify_core.tool_check import (
    DEFAULT_TIMEOUT,
    FAILED,
    NOT_APPLICABLE,
    NOT_IMPLEMENTED,
    PASSED,
    ToolCheckResult,
    check_tool,
)

from speccify_cli.commands.expand import agent_root, expansions_path

tool_app = typer.Typer(
    name="tool",
    help="Work with the tools under .agent/tools/.",
    no_args_is_help=True,
    add_completion=False,
)


@dataclass(frozen=True)
class ToolCheckReport:
    platform: str
    results: list[ToolCheckResult] = field(default_factory=list)

    @property
    def failed(self) -> list[ToolCheckResult]:
        return [r for r in self.results if r.status == FAILED]

    @property
    def verified(self) -> list[ToolCheckResult]:
        return [r for r in self.results if r.verified]

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "platform": self.platform,
            "tools": [r.to_dict() for r in self.results],
        }


def run_tool_check(
    project_dir: Path,
    names: list[str] | None = None,
    *,
    platform: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    today: date | None = None,
) -> ToolCheckReport:
    """Check the named tools (default: all under `.agent/tools/`) and update the record."""
    platform = platform or current_platform()
    tools_root = agent_root(project_dir) / TOOLS_DIR
    path = expansions_path(project_dir)
    record = Expansions.load(path)

    if names:
        for name in names:
            if not (tools_root / name / TOOL_FILENAME).is_file():
                raise FileNotFoundError(
                    f"No {AGENT_DIR}/{TOOLS_DIR}/{name}/{TOOL_FILENAME} in {project_dir}. "
                    f"Run `speccify expand` first."
                )
        selected = list(names)
    else:
        on_disk = (
            sorted(p.name for p in tools_root.iterdir() if (p / TOOL_FILENAME).is_file())
            if tools_root.is_dir()
            else []
        )
        selected = sorted({*record.tools, *on_disk})
        selected = [n for n in selected if (tools_root / n / TOOL_FILENAME).is_file()]

    report = ToolCheckReport(platform=platform)
    tools = dict(record.tools)
    stamp = (today or date.today()).isoformat()
    for name in selected:
        result = check_tool(tools_root / name, platform=platform, timeout=timeout)
        report.results.append(result)
        if result.status in (NOT_APPLICABLE, NOT_IMPLEMENTED):
            continue
        known = tools.get(name)
        if known is None:
            # Projekteigenes Tool (nicht aus `expand`): trotzdem aufzeichnen —
            # eine App will den Status sehen, und W-B (zurückgeben) braucht den
            # Spec-Hash. Herkunft bleibt leer, das unterscheidet es.
            spec_bytes = (tools_root / name / TOOL_FILENAME).read_bytes()
            known = ToolRecord(from_skills=(), spec_sha256=sha256_text(spec_bytes), platforms={})
        platforms = dict(known.platforms)
        entry = {"file": result.implementation or ""}
        if result.verified:
            entry["status"] = VERIFIED
            entry["checked"] = stamp
        else:
            entry["status"] = IMPLEMENTED
        platforms[platform] = entry
        tools[name] = ToolRecord(
            from_skills=known.from_skills, spec_sha256=known.spec_sha256, platforms=platforms
        )
    if tools != record.tools:
        Expansions(skills=record.skills, tools=tools, schema_version=record.schema_version).write(
            path
        )
    return report


@tool_app.command("check")
def tool_check_command(
    names: list[str] = typer.Argument(  # noqa: B008
        None, help="Tool names under .agent/tools/ (default: all of them)."
    ),
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
    platform: str | None = typer.Option(
        None, "--platform", help="macos, linux or windows (default: this machine)."
    ),
    timeout: float = typer.Option(
        DEFAULT_TIMEOUT, "--timeout", help="Seconds each example may take before it fails."
    ),
    as_json: bool = typer.Option(False, "--json", help="Print the full report as JSON."),
) -> None:
    """Run each tool spec's examples against the implementation for this platform."""
    try:
        report = run_tool_check(project_dir, names or None, platform=platform, timeout=timeout)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"x speccify tool check failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if as_json:
        typer.echo(json.dumps(report.to_dict(), indent=2))
        raise typer.Exit(code=0 if report.ok else 1)

    if not report.results:
        typer.echo(f"No tools under {AGENT_DIR}/{TOOLS_DIR}/. Run `speccify expand` first.")
        return

    for result in report.results:
        if result.status == PASSED:
            typer.echo(
                f"ok   {result.name}  {len(result.cases)} example(s) pass "
                f"({result.implementation}) -> verified for {report.platform}"
            )
        elif result.status == FAILED:
            failed = [c for c in result.cases if not c.passed]
            typer.echo(
                f"x    {result.name}  {len(failed)} of {len(result.cases)} example(s) fail "
                f"({result.implementation})"
            )
            for case in failed:
                typer.echo(f"       '{case.title}': {case.detail}")
                if case.stderr and "stderr" not in case.detail:
                    typer.echo(f"         stderr: {case.stderr.splitlines()[-1]}")
        else:
            typer.echo(f"-    {result.name}  {result.status}: {result.detail}")

    typer.echo(
        f"\n{len(report.verified)} verified, {len(report.failed)} failed, "
        f"{len(report.results) - len(report.verified) - len(report.failed)} not run "
        f"on {report.platform}."
    )
    if not report.ok:
        raise typer.Exit(code=1)
