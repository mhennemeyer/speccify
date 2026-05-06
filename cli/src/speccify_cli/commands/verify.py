"""`speccify verify`: schließt den Reproduzierbarkeits-Kreis.

Phase 1a:
- Liest Manifest und Lockfile.
- Re-resolved Manifest gegen die Registry und vergleicht (id, version, sha256, target).
- Re-rendered jede Spec in einem Temp-Verzeichnis und vergleicht Output-Hashes mit
  `generated_files_sha256` aus dem Lockfile.
- Liest die tatsächlichen Output-Dateien aus `--out` und prüft, dass sie mit den
  Lockfile-Hashes übereinstimmen (Drift-Detection).
- Exit 0 nur, wenn *alle* Vergleiche grün sind; sonst Exit 1 mit Liste der Probleme.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import typer
from speccify_core import (
    Lockfile,
    LockfileError,
    Resolver,
    ResolverError,
)
from speccify_core.codegen import render_to_files
from speccify_core.manifest import ManifestError
from speccify_core.registry import RegistryError, Version

from speccify_cli.commands._workspace import WorkspaceContext


def run_verify(
    project_dir: Path,
    out_dir: Path,
    registry_override: Path | None = None,
) -> list[str]:
    """Gibt eine Liste von Problemen zurück. Leere Liste = grün."""
    problems: list[str] = []

    ctx = WorkspaceContext.load(project_dir, registry_override=registry_override)
    if not ctx.lockfile_path.is_file():
        return [f"Kein Lockfile in {project_dir} (bitte `speccify lock` ausführen)."]

    lockfile = Lockfile.load(ctx.lockfile_path)

    # 1) Re-resolve und vergleiche mit Lockfile-Einträgen.
    graph = Resolver(ctx.registry).resolve(ctx.manifest)
    if graph.target != lockfile.target:
        problems.append(f"Target-Drift: Manifest={graph.target!r}, Lockfile={lockfile.target!r}.")

    resolved_by_id = {r.spec_id: r for r in graph.resolutions}
    locked_by_id = {e.id: e for e in lockfile.entries}

    only_in_lock = sorted(set(locked_by_id) - set(resolved_by_id))
    only_in_resolve = sorted(set(resolved_by_id) - set(locked_by_id))
    for spec_id in only_in_lock:
        problems.append(f"Spec '{spec_id}' im Lockfile, aber nicht mehr aufgelöst.")
    for spec_id in only_in_resolve:
        problems.append(f"Spec '{spec_id}' aufgelöst, aber nicht im Lockfile.")

    for spec_id in sorted(set(locked_by_id) & set(resolved_by_id)):
        entry = locked_by_id[spec_id]
        resolution = resolved_by_id[spec_id]
        if str(resolution.version) != entry.version:
            problems.append(
                f"Versions-Drift für {spec_id}: "
                f"Lockfile={entry.version}, aufgelöst={resolution.version}."
            )
        if resolution.spec_sha256 != entry.sha256:
            problems.append(
                f"Spec-Hash-Drift für {spec_id}@{entry.version}: "
                f"Lockfile={entry.sha256}, neu berechnet={resolution.spec_sha256}."
            )

    # 2) Re-rendere jede Spec und vergleiche Output-Hashes.
    for entry in lockfile.entries:
        try:
            spec = ctx.registry.fetch(entry.id, Version.parse(entry.version))
        except RegistryError as exc:
            problems.append(str(exc))
            continue
        rendered = render_to_files(spec, lockfile.target)

        expected = {f.path: f.sha256 for f in entry.generated_files_sha256}
        if not expected:
            problems.append(
                f"Spec {entry.id}@{entry.version} hat keine `generated_files_sha256` "
                f"(bitte `speccify pull` ausführen)."
            )
            continue

        rendered_paths = set(rendered.keys())
        expected_paths = set(expected.keys())
        for path in sorted(rendered_paths - expected_paths):
            problems.append(f"Output {path} (re-rendered) nicht im Lockfile.")
        for path in sorted(expected_paths - rendered_paths):
            problems.append(f"Output {path} (Lockfile) nicht erneut gerendert.")

        for path in sorted(rendered_paths & expected_paths):
            digest = f"sha256:{hashlib.sha256(rendered[path]).hexdigest()}"
            if digest != expected[path]:
                problems.append(
                    f"Re-Render-Drift für {path}: Lockfile={expected[path]}, neu={digest}."
                )

            # 3) Vergleiche Lockfile-Hash mit Datei auf Disk.
            on_disk = out_dir / path
            if not on_disk.is_file():
                problems.append(f"Output-Datei fehlt auf Disk: {on_disk}.")
                continue
            disk_digest = f"sha256:{hashlib.sha256(on_disk.read_bytes()).hexdigest()}"
            if disk_digest != expected[path]:
                problems.append(
                    f"Disk-Drift für {on_disk}: Lockfile={expected[path]}, Datei={disk_digest}."
                )

    return problems


def verify_command(
    project_dir: Path | None = typer.Option(  # noqa: B008
        None,
        "--project",
        "-p",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Projekt-Verzeichnis mit speccify.yaml/speccify.lock (Default: aktuelles Verz.).",
    ),
    out: Path = typer.Option(  # noqa: B008
        Path("./out"),
        "--out",
        file_okay=False,
        dir_okay=True,
        help="Verzeichnis mit gerenderten Dateien.",
    ),
    registry: Path | None = typer.Option(  # noqa: B008
        None,
        "--registry",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Optionale Registry-Pfad-Überschreibung.",
    ),
) -> None:
    """Prüft, dass Manifest, Lockfile und gerenderte Dateien zueinander passen."""
    project = project_dir or Path.cwd()
    try:
        problems = run_verify(project, out_dir=out, registry_override=registry)
    except (ManifestError, RegistryError, LockfileError, ResolverError, FileNotFoundError) as exc:
        typer.echo(f"✗ speccify verify fehlgeschlagen: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if problems:
        typer.echo("✗ speccify verify: Drift erkannt:", err=True)
        for p in problems:
            typer.echo(f"    - {p}", err=True)
        raise typer.Exit(code=1)

    typer.echo("✓ speccify verify: Manifest, Lockfile und Output sind konsistent.")
