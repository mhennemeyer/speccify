"""`speccify lint`: validate playbook bundles."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from speccify_core import ASSET_DIR, PLAYBOOK_FILENAME, validate_playbook


def lint_bundle(bundle_dir: Path) -> list[str]:
    """Validate one bundle directory; returns formatted issues."""
    playbook_path = bundle_dir / PLAYBOOK_FILENAME
    if not playbook_path.is_file():
        return [f"$: no {PLAYBOOK_FILENAME} in {bundle_dir}"]
    try:
        data = yaml.safe_load(playbook_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"$: invalid YAML: {exc}"]

    files = {PLAYBOOK_FILENAME}
    asset_root = bundle_dir / ASSET_DIR
    if asset_root.is_dir():
        files |= {
            asset.relative_to(bundle_dir).as_posix()
            for asset in asset_root.rglob("*")
            if asset.is_file()
        }
    return [issue.format() for issue in validate_playbook(data, bundle_files=files)]


def find_bundles(root: Path) -> list[Path]:
    """Every bundle directory below `root` (a directory holding a playbook.yaml)."""
    if (root / PLAYBOOK_FILENAME).is_file():
        return [root]
    return sorted(path.parent for path in root.rglob(PLAYBOOK_FILENAME))


def lint_command(
    paths: list[Path] = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        readable=True,
        help="Playbook bundle directories (or a directory tree containing them).",
    ),
) -> None:
    """Validate playbooks: schema, cross-references and assets."""
    bundles: list[Path] = []
    for path in paths:
        bundles.extend(find_bundles(path if path.is_dir() else path.parent))
    if not bundles:
        typer.echo("No playbooks found.", err=True)
        raise typer.Exit(code=1)

    failed = 0
    for bundle in bundles:
        issues = lint_bundle(bundle)
        if not issues:
            typer.echo(f"ok  {bundle}")
            continue
        failed += 1
        typer.echo(f"fail {bundle}", err=True)
        for issue in issues:
            typer.echo(f"     {issue}", err=True)

    if failed:
        typer.echo(f"\n{failed} of {len(bundles)} playbooks have problems.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"\n{len(bundles)} playbook(s) validated.")
