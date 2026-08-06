"""`speccify check`: is the knowledge in these playbooks still current?

`lint` asks whether a playbook is well-formed. `check` asks whether it is still
*true*: how old its sources are, and — with `--links` — whether they still
resolve. Network checks are opt-in so a normal run stays fast and hermetic.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import typer
import yaml
from speccify_core import (
    ASSET_DIR,
    PLAYBOOK_FILENAME,
    STALE_SOURCE_DAYS,
    Finding,
    check_links,
    check_playbook,
    parse_playbook,
)

from speccify_cli.commands.lint import find_bundles


def check_bundle(
    bundle_dir: Path,
    *,
    links: bool = False,
    today: date | None = None,
    stale_days: int = STALE_SOURCE_DAYS,
) -> list[Finding]:
    """Health of one bundle: structure, source age and optionally reachability."""
    playbook_path = bundle_dir / PLAYBOOK_FILENAME
    if not playbook_path.is_file():
        return [Finding("error", "$", f"no {PLAYBOOK_FILENAME} in {bundle_dir}")]
    try:
        data = yaml.safe_load(playbook_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [Finding("error", "$", f"invalid YAML: {exc}")]

    files = {PLAYBOOK_FILENAME}
    asset_root = bundle_dir / ASSET_DIR
    if asset_root.is_dir():
        files |= {
            asset.relative_to(bundle_dir).as_posix()
            for asset in asset_root.rglob("*")
            if asset.is_file()
        }

    findings = check_playbook(data, bundle_files=files, today=today, stale_days=stale_days)
    if links and not any(finding.is_error for finding in findings):
        findings.extend(check_links(parse_playbook(data)))
    return findings


def check_command(
    paths: list[Path] = typer.Argument(  # noqa: B008
        ..., exists=True, readable=True, help="Playbook bundles (or a tree containing them)."
    ),
    links: bool = typer.Option(
        False, "--links/--no-links", help="Also check that every source URL still resolves."
    ),
    stale_days: int = typer.Option(
        STALE_SOURCE_DAYS, "--stale-days", help="Warn about sources older than this."
    ),
) -> None:
    """Check whether playbooks are still current: source age and dead links."""
    bundles: list[Path] = []
    for path in paths:
        bundles.extend(find_bundles(path if path.is_dir() else path.parent))
    if not bundles:
        typer.echo("No playbooks found.", err=True)
        raise typer.Exit(code=1)

    errors = warnings = 0
    for bundle in bundles:
        findings = check_bundle(bundle, links=links, stale_days=stale_days)
        if not findings:
            typer.echo(f"ok  {bundle}")
            continue
        typer.echo(f"--- {bundle}")
        for finding in findings:
            typer.echo(f"    {finding.format()}", err=finding.is_error)
            if finding.is_error:
                errors += 1
            else:
                warnings += 1

    summary = f"\n{len(bundles)} playbook(s): {errors} error(s), {warnings} warning(s)."
    if errors:
        typer.echo(summary, err=True)
        raise typer.Exit(code=1)
    typer.echo(summary)
