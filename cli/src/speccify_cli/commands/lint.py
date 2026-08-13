"""`speccify lint`: validate skill directories against the specification.

Also still validates `playbook.yaml` bundles — a migration leftover that goes
away with the last one in the tree.
"""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from speccify_core import ASSET_DIR, PLAYBOOK_FILENAME, validate_playbook
from speccify_core.skill import SkillError, validate_skill
from speccify_core.skill_check import find_skills, load_skill


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


def lint_skill(directory: Path) -> list[str]:
    """Validate one skill directory against the Agent Skills specification."""
    try:
        skill, files = load_skill(directory)
    except SkillError as exc:
        return [f"$: {exc}"]
    return [issue.format() for issue in validate_skill(skill, bundle_files=files)]


def lint_command(
    paths: list[Path] = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        readable=True,
        help="Skill directories (or a directory tree containing them).",
    ),
) -> None:
    """Validate skills against the Agent Skills specification."""
    targets: list[tuple[Path, bool]] = []
    for path in paths:
        root = path if path.is_dir() else path.parent
        targets += [(d, True) for d in find_skills(root)]
        targets += [(d, False) for d in find_bundles(root)]
    if not targets:
        typer.echo("No skills found.", err=True)
        raise typer.Exit(code=1)

    failed = 0
    for bundle, is_skill in targets:
        issues = lint_skill(bundle) if is_skill else lint_bundle(bundle)
        if not issues:
            typer.echo(f"ok  {bundle}")
            continue
        failed += 1
        typer.echo(f"fail {bundle}", err=True)
        for issue in issues:
            typer.echo(f"     {issue}", err=True)

    if failed:
        typer.echo(f"\n{failed} of {len(targets)} skills have problems.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"\n{len(targets)} skill(s) validated.")
