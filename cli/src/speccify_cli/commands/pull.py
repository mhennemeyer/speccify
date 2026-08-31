"""`speccify pull`: materialise the locked skills as they are upstream.

Default target is the cache `.agent/speccify/cache/` (gitignored). What the
agent reads is not this but `.agent/skills/`, which `speccify expand` derives
from the same bundles — resolved, normalised, project-specific. `pull` remains
for the moment you want the untouched upstream next to it: to diff, to read
what changed, or to drop a skill somewhere throwaway.

The layout there is **flat**: `<out>/<name>/SKILL.md`. `name` is the lookup key,
so two skills of the same name from different scopes cannot both be installed;
that collision is reported rather than silently resolved by whoever writes last.
"""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core import Lockfile, LockfileError, RegistryError, Version, bundle_sha256

from speccify_cli.commands._context import ProjectContext, fetch_bundle

DEFAULT_OUT_DIR = "./.agent/speccify/cache"


def run_pull(
    project_dir: Path,
    out_dir: Path,
    *,
    library_override: Path | None = None,
    offline: bool = False,
) -> list[Path]:
    """Write every locked skill to `<out_dir>/<name>/`; returns the files written."""
    context = ProjectContext.load(project_dir, library_override=library_override, offline=offline)
    if not context.lockfile_path.is_file():
        raise LockfileError(f"No lockfile in {project_dir}. Run `speccify lock` first.")
    lockfile = Lockfile.load(context.lockfile_path)

    written: list[Path] = []
    taken: dict[str, str] = {}
    for entry in lockfile.entries:
        bundle = fetch_bundle(context.libraries, entry.id, Version.parse(entry.version))
        actual = bundle_sha256(bundle.files)
        if actual != entry.bundle_sha256:
            raise RegistryError(
                f"{entry.id}@{entry.version}: bundle hash differs from the lockfile "
                f"({actual} != {entry.bundle_sha256}). Someone moved a tag."
            )
        # Flat by name — host adapters look up `<name>/SKILL.md` by this key.
        name = bundle.declared_id.rsplit("/", 1)[-1]
        if name in taken and taken[name] != bundle.declared_id:
            raise RegistryError(
                f"Two skills would install as '{name}': {taken[name]} and "
                f"{bundle.declared_id}. Skill names are the lookup key and have to be "
                f"unique — rename one, or drop one from the manifest."
            )
        taken[name] = bundle.declared_id
        target = out_dir / name
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
        Path(DEFAULT_OUT_DIR), "--out", help="Where to materialise the skills."
    ),
    library: Path | None = typer.Option(  # noqa: B008
        None, "--library", help="Local skill library (default: from the manifest)."
    ),
    offline: bool = typer.Option(
        False, "--offline/--no-offline", help="Only read cached git sources, never the network."
    ),
) -> None:
    """Materialise the locked skills untouched, as upstream has them (default: the cache)."""
    try:
        written = run_pull(project_dir, out, library_override=library, offline=offline)
    except (LockfileError, RegistryError, FileNotFoundError) as exc:
        typer.echo(f"x speccify pull failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    for path in written:
        typer.echo(f"ok {path}")
    typer.echo(f"\n{len(written)} file(s) written to {out}.")
