"""`speccify pull`: materialise the locked bundles into a directory.

Agents usually read playbooks over MCP, but having them on disk makes them
greppable, diffable and readable offline — assets included.
"""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core import Lockfile, LockfileError, RegistryError, Version, bundle_sha256

from speccify_cli.commands._context import ProjectContext, fetch_bundle

DEFAULT_OUT_DIR = "./speccify_playbooks"


def run_pull(
    project_dir: Path,
    out_dir: Path,
    *,
    library_override: Path | None = None,
    offline: bool = False,
) -> list[Path]:
    """Write every locked bundle to `<out_dir>/<scope>/<name>/`; returns the files written."""
    context = ProjectContext.load(project_dir, library_override=library_override, offline=offline)
    if not context.lockfile_path.is_file():
        raise LockfileError(f"No lockfile in {project_dir}. Run `speccify lock` first.")
    lockfile = Lockfile.load(context.lockfile_path)

    written: list[Path] = []
    for entry in lockfile.entries:
        bundle = fetch_bundle(context.libraries, entry.id, Version.parse(entry.version))
        actual = bundle_sha256(bundle.files)
        if actual != entry.bundle_sha256:
            raise RegistryError(
                f"{entry.id}@{entry.version}: bundle hash differs from the lockfile "
                f"({actual} != {entry.bundle_sha256}). Someone moved a tag."
            )
        target = out_dir / bundle.declared_id.lstrip("@")
        for relative, data in sorted(bundle.files.items()):
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            written.append(path)
    return written


def pull_command(
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
    out: Path = typer.Option(  # noqa: B008
        Path(DEFAULT_OUT_DIR), "--out", help="Where to materialise the bundles."
    ),
    library: Path | None = typer.Option(  # noqa: B008
        None, "--library", help="Local playbook library (default: from the manifest)."
    ),
    offline: bool = typer.Option(
        False, "--offline/--no-offline", help="Only read cached git sources, never the network."
    ),
) -> None:
    """Materialise the locked playbooks (including assets) into a directory."""
    try:
        written = run_pull(project_dir, out, library_override=library, offline=offline)
    except (LockfileError, RegistryError, FileNotFoundError) as exc:
        typer.echo(f"x speccify pull failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    for path in written:
        typer.echo(f"ok {path}")
    typer.echo(f"\n{len(written)} file(s) written to {out}.")
