"""`speccify show`: read a skill without installing it.

Once a skill is in `.claude/skills/` the agent reads it from disk — that is the
whole point of storing skills in their own format. This command is for the
moment *before* that: what is in this thing, and do I want it?

So the payload leads with the body. The inferred structure (steps, sources)
comes along because it is cheap and answers "how big is this" and "how old is
what it rests on" without reading all of it.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from speccify_core import RegistryError, parse_uses_entry
from speccify_core.skill_check import tools_from_bundle
from speccify_core.tool import Tool

from speccify_cli.commands._context import ProjectContext, fetch_bundle, list_versions


def run_show(
    project_dir: Path,
    reference: str,
    *,
    library_override: Path | None = None,
    offline: bool = False,
) -> dict:
    """Return a skill as a plain dict."""
    context = ProjectContext.load(project_dir, library_override=library_override, offline=offline)
    skill_id, _ = parse_uses_entry(reference)
    versions = list_versions(context.libraries, skill_id)
    if not versions:
        raise RegistryError(f"'{skill_id}' is not available locally or as a git source.")
    bundle = fetch_bundle(context.libraries, skill_id, versions[-1])
    if not bundle.is_skill:
        raise RegistryError(f"'{skill_id}' is not a skill — the bundle has no SKILL.md.")
    skill = bundle.skill()

    return {
        "id": skill.qualified_id,
        "name": skill.name,
        "source": bundle.source_id,
        "version": skill.version,
        "description": skill.description,
        "license": skill.license,
        "compatibility": skill.compatibility,
        "stack": list(skill.stack),
        "platforms": list(skill.platforms),
        "uses": list(skill.uses),
        "deprecated": skill.deprecated,
        "superseded_by": skill.superseded_by,
        # The instructions themselves — what the agent would actually follow.
        "body": skill.body,
        "steps": [
            {"number": step.number, "title": step.title, "verify": step.verify}
            for step in skill.steps
        ],
        "sources": [
            {"title": source.title, "url": source.url, "retrieved": source.retrieved}
            for source in skill.sources
        ],
        "files": sorted(path for path in bundle.files if path != "SKILL.md"),
        # Tool specs: shallow here, like the skill list — `tool_get` has the rest.
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "platforms": list(tool.platforms),
                "requires": list(tool.requires),
                "runtime": list(tool.runtime),
                "examples": len(tool.examples),
            }
            for tool in tools_from_bundle(bundle.files).values()
            if isinstance(tool, Tool)
        ],
    }


def tool_as_dict(tool: Tool, *, files: list[str]) -> dict:
    """The whole contract of one tool — what an agent implements against."""
    return {
        "name": tool.name,
        "description": tool.description,
        "inputs": tool.inputs,
        "outputs": tool.outputs,
        "effects": tool.effects,
        "requires": list(tool.requires),
        "runtime": list(tool.runtime),
        "platforms": list(tool.platforms),
        "body": tool.body,
        "examples": [
            {"title": e.title, "input": e.input, "output": e.output} for e in tool.examples
        ],
        # Reference implementations and fixtures that ship beside the spec.
        "files": files,
    }


def show_command(
    reference: str = typer.Argument(..., help="Skill id or git source."),
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
    library: Path | None = typer.Option(  # noqa: B008
        None, "--library", help="Local skill library (default: from the manifest)."
    ),
    offline: bool = typer.Option(
        False, "--offline/--no-offline", help="Only read cached git sources, never the network."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON (for agents and scripts)."),
) -> None:
    """Print a skill: what it is, what it builds on, and how old its sources are."""
    try:
        data = run_show(project_dir, reference, library_override=library, offline=offline)
    except (RegistryError, FileNotFoundError, ValueError) as exc:
        typer.echo(f"x speccify show failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if as_json:
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    typer.echo(f"{data['id']}@{data['version'] or '?'}")
    typer.echo(f"  {data['description']}")
    if data["deprecated"]:
        successor = f" — use {data['superseded_by']}" if data["superseded_by"] else ""
        typer.echo(f"  WITHDRAWN: {data['deprecated']}{successor}", err=True)
    if data["compatibility"]:
        typer.echo(f"  {data['compatibility']}")
    axes = ", ".join([*data["stack"], *data["platforms"]])
    if axes:
        typer.echo(f"  {axes}")
    for used in data["uses"]:
        typer.echo(f"  builds on: {used}")

    if data["steps"]:
        typer.echo(f"\n{len(data['steps'])} step(s):")
        for step in data["steps"]:
            prefix = f"{step['number']}. " if step["number"] is not None else "- "
            typer.echo(f"  {prefix}{step['title']}")
    if data["sources"]:
        typer.echo(f"\n{len(data['sources'])} source(s):")
        for source in data["sources"]:
            typer.echo(f"  {source['title']} ({source['retrieved'] or 'no date'})")
    if data["tools"]:
        typer.echo(f"\n{len(data['tools'])} tool spec(s):")
        for tool in data["tools"]:
            where = f" [{', '.join(tool['platforms'])}]" if tool["platforms"] else ""
            typer.echo(f"  {tool['name']}{where} — {tool['examples']} example(s)")
    if data["files"]:
        typer.echo(f"\nfiles: {', '.join(data['files'])}")
