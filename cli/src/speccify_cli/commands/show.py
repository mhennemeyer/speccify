"""`speccify show`: read a playbook — the whole thing or a single step.

This is the command an agent reaches for when it wants the knowledge rather
than the files.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from speccify_core import RegistryError, parse_playbook, parse_uses_entry

from speccify_cli.commands._context import ProjectContext, fetch_bundle, list_versions


def run_show(
    project_dir: Path,
    reference: str,
    *,
    step_id: str | None = None,
    library_override: Path | None = None,
    offline: bool = False,
) -> dict:
    """Return a playbook (or one step) as a plain dict."""
    context = ProjectContext.load(project_dir, library_override=library_override, offline=offline)
    playbook_id, _ = parse_uses_entry(reference)
    versions = list_versions(context.libraries, playbook_id)
    if not versions:
        raise RegistryError(f"'{playbook_id}' is not available locally or as a git source.")
    bundle = fetch_bundle(context.libraries, playbook_id, versions[-1])
    playbook = parse_playbook(bundle.parsed())

    def source_dict(source_id: str) -> dict:
        source = playbook.source(source_id)
        return (
            {}
            if source is None
            else {
                "id": source.id,
                "title": source.title,
                "url": source.url,
                "retrieved": source.retrieved,
                "note": source.note,
            }
        )

    def step_dict(step) -> dict:
        return {
            "id": step.id,
            "title": step.title,
            "detail": step.detail,
            "uses": step.uses,
            "verify": step.verify,
            "assets": list(step.assets),
            "sources": [source_dict(s) for s in step.sources],
        }

    if step_id is not None:
        step = playbook.step(step_id)
        if step is None:
            known = ", ".join(s.id for s in playbook.steps)
            raise RegistryError(f"'{playbook_id}' has no step '{step_id}'. Known steps: {known}.")
        return {"playbook": playbook.id, "version": playbook.version, "step": step_dict(step)}

    return {
        "id": playbook.id,
        "source": bundle.source_id,
        "version": playbook.version,
        "title": playbook.title,
        "summary": playbook.summary,
        "applies_to": {
            "platforms": list(playbook.applies_to.platforms),
            "requires": list(playbook.applies_to.requires),
            "keywords": list(playbook.applies_to.keywords),
        },
        "prerequisites": list(playbook.prerequisites),
        "steps": [step_dict(step) for step in playbook.steps],
        "sources": [source_dict(s.id) for s in playbook.sources],
        "pitfalls": list(playbook.pitfalls),
        "assets": list(bundle.asset_paths),
    }


def show_command(
    reference: str = typer.Argument(..., help="Playbook id or git source."),
    step: str | None = typer.Option(None, "--step", help="Show only this step."),
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
    library: Path | None = typer.Option(  # noqa: B008
        None, "--library", help="Local playbook library (default: from the manifest)."
    ),
    offline: bool = typer.Option(
        False, "--offline/--no-offline", help="Only read cached git sources, never the network."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON (for agents and scripts)."),
) -> None:
    """Print a playbook, or a single step of it."""
    try:
        data = run_show(
            project_dir, reference, step_id=step, library_override=library, offline=offline
        )
    except (RegistryError, FileNotFoundError, ValueError) as exc:
        typer.echo(f"x {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if as_json:
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if step is not None:
        one = data["step"]
        typer.echo(f"{data['playbook']}@{data['version']} - step {one['id']}: {one['title']}")
        if one["uses"]:
            typer.echo(f"  delegates to: {one['uses']}")
        if one["detail"]:
            typer.echo(f"\n{one['detail']}")
        if one["verify"]:
            typer.echo(f"\nverify: {one['verify']}")
        for source in one["sources"]:
            typer.echo(
                f"source: {source['title']} — {source['url']} (retrieved {source['retrieved']})"
            )
        return

    typer.echo(f"{data['id']}@{data['version']} — {data['title']}")
    typer.echo(f"{data['summary']}\n")
    for prerequisite in data["prerequisites"]:
        typer.echo(f"  requires: {prerequisite}")
    typer.echo(f"\nSteps ({len(data['steps'])}):")
    for index, one in enumerate(data["steps"], start=1):
        suffix = f"  -> {one['uses']}" if one["uses"] else ""
        typer.echo(f"  {index}. [{one['id']}] {one['title']}{suffix}")
    if data["pitfalls"]:
        typer.echo("\nPitfalls:")
        for pitfall in data["pitfalls"]:
            typer.echo(f"  - {pitfall}")
    if data["sources"]:
        typer.echo("\nSources:")
        for source in data["sources"]:
            typer.echo(f"  - {source['title']} ({source['retrieved']}) {source['url']}")
    typer.echo("\nRead a single step with: speccify show <id> --step <step-id>")
