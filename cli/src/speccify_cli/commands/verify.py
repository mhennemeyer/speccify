"""`speccify verify`: schließt den Reproduzierbarkeits-Kreis.

Phase 1b Step 5b:
- Re-render läuft über den Codegen-Dispatcher `render_for_target`, der für
  `target == "react"` einen `ReplayCacheClient` braucht (Default: eingecheckter
  Replay-Cache; Override via `--cache-dir`/`SPECCIFY_CACHE_DIR`).
- Neue Flags `--offline/--no-offline` und `--cache-dir` analog zu `pull`.
- Zusätzlich wird der Generator-Pin pro LLM-Eintrag verifiziert: `model`,
  `prompt_version`, `seed` und `cache_key` müssen mit dem aktuellen
  Re-Render-Lauf übereinstimmen — verhindert Modell-/Prompt-Drift.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import typer
from speccify_core import (
    CacheMissError,
    CodegenError,
    LlmGeneratorPin,
    Lockfile,
    LockfileError,
    Resolver,
    ResolverError,
    render_for_target,
)
from speccify_core.manifest import ManifestError
from speccify_core.registry import RegistryError, Version

from speccify_cli.commands._llm_client import build_replay_client
from speccify_cli.commands._workspace import WorkspaceContext


def run_verify(
    project_dir: Path,
    out_dir: Path,
    registry_override: Path | None = None,
    *,
    offline: bool = True,
    cache_dir: Path | None = None,
) -> list[str]:
    """Gibt eine Liste von Problemen zurück. Leere Liste = grün.

    Für nicht-fatale Hinweise (z.B. yanked Versionen) verwende stattdessen
    :func:`run_verify_with_warnings`, das ein ``(problems, warnings)``-Tuple liefert.
    """
    problems, _warnings = run_verify_with_warnings(
        project_dir,
        out_dir=out_dir,
        registry_override=registry_override,
        offline=offline,
        cache_dir=cache_dir,
    )
    return problems


def run_verify_with_warnings(
    project_dir: Path,
    out_dir: Path,
    registry_override: Path | None = None,
    *,
    offline: bool = True,
    cache_dir: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Wie :func:`run_verify`, gibt aber zusätzlich nicht-fatale Warnungen zurück.

    Warnungen brechen den Verify-Run nicht (Exit 0), werden aber an stderr
    gemeldet. In Phase 2 nutzen wir das für ``yank_status == 'yanked'``-
    Einträge im Lockfile: das Lockfile bleibt valide, der User wird aber
    informiert, dass die genutzte Version vom Registry zurückgezogen wurde.
    """
    problems: list[str] = []
    warnings: list[str] = []

    ctx = WorkspaceContext.load(project_dir, registry_override=registry_override)
    if not ctx.lockfile_path.is_file():
        return (
            [f"Kein Lockfile in {project_dir} (bitte `speccify lock` ausführen)."],
            warnings,
        )

    lockfile = Lockfile.load(ctx.lockfile_path)

    # Yank-Warnungen aus dem Lockfile aufsammeln (Phase 2 Stage 5).
    for entry in lockfile.entries:
        if entry.yank_status == "yanked":
            reason = f" (reason: {entry.yank_reason})" if entry.yank_reason else ""
            warnings.append(
                f"Spec {entry.id}@{entry.version} wurde im Registry geyanked{reason}. "
                f"Bitte auf eine neuere Version aktualisieren."
            )

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

    # 2) Re-rendere jede Spec und vergleiche Output-Hashes + Generator-Pin.
    llm_client = build_replay_client(offline=offline, cache_dir=cache_dir)
    for entry in lockfile.entries:
        try:
            spec = ctx.registry.fetch(entry.id, Version.parse(entry.version))
        except RegistryError as exc:
            problems.append(str(exc))
            continue
        try:
            rendered = render_for_target(spec, lockfile.target, llm_client=llm_client)
        except (CacheMissError, CodegenError) as exc:
            problems.append(f"Re-Render für {entry.id}@{entry.version} fehlgeschlagen: {exc}")
            continue

        # Generator-Pin-Konsistenz für LLM-Einträge.
        if isinstance(entry.generator, LlmGeneratorPin):
            if rendered.cache_key is None:
                problems.append(
                    f"Generator-Pin-Drift für {entry.id}: Lockfile=llm, Re-Render=template."
                )
            else:
                expected_cache_key = f"sha256:{rendered.cache_key.digest()}"
                if entry.generator.model != rendered.cache_key.model:
                    problems.append(
                        f"Modell-Drift für {entry.id}: Lockfile={entry.generator.model}, "
                        f"Re-Render={rendered.cache_key.model}."
                    )
                if entry.generator.prompt_version != rendered.cache_key.prompt_version:
                    problems.append(
                        f"Prompt-Version-Drift für {entry.id}: "
                        f"Lockfile={entry.generator.prompt_version}, "
                        f"Re-Render={rendered.cache_key.prompt_version}."
                    )
                if entry.generator.seed != rendered.cache_key.seed:
                    problems.append(
                        f"Seed-Drift für {entry.id}: Lockfile={entry.generator.seed}, "
                        f"Re-Render={rendered.cache_key.seed}."
                    )
                if entry.generator.cache_key != expected_cache_key:
                    problems.append(
                        f"Cache-Key-Drift für {entry.id}: Lockfile={entry.generator.cache_key}, "
                        f"Re-Render={expected_cache_key}."
                    )

        expected = {f.path: f.sha256 for f in entry.generated_files_sha256}
        if not expected:
            problems.append(
                f"Spec {entry.id}@{entry.version} hat keine `generated_files_sha256` "
                f"(bitte `speccify pull` ausführen)."
            )
            continue

        rendered_paths = set(rendered.files.keys())
        expected_paths = set(expected.keys())
        for path in sorted(rendered_paths - expected_paths):
            problems.append(f"Output {path} (re-rendered) nicht im Lockfile.")
        for path in sorted(expected_paths - rendered_paths):
            problems.append(f"Output {path} (Lockfile) nicht erneut gerendert.")

        for path in sorted(rendered_paths & expected_paths):
            digest = f"sha256:{hashlib.sha256(rendered.files[path]).hexdigest()}"
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

    return problems, warnings


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
    offline: bool = typer.Option(  # noqa: B008
        True,
        "--offline/--no-offline",
        help="Nur Replay-Cache benutzen (Default).",
    ),
    cache_dir: Path | None = typer.Option(  # noqa: B008
        None,
        "--cache-dir",
        file_okay=False,
        dir_okay=True,
        help="Replay-Cache-Pfad (Default: tests/fixtures/llm-cache im Repo "
        "bzw. $SPECCIFY_CACHE_DIR).",
    ),
) -> None:
    """Prüft, dass Manifest, Lockfile und gerenderte Dateien zueinander passen."""
    project = project_dir or Path.cwd()
    try:
        problems, warnings = run_verify_with_warnings(
            project,
            out_dir=out,
            registry_override=registry,
            offline=offline,
            cache_dir=cache_dir,
        )
    except (ManifestError, RegistryError, LockfileError, ResolverError, FileNotFoundError) as exc:
        typer.echo(f"✗ speccify verify fehlgeschlagen: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for w in warnings:
        typer.echo(f"⚠ {w}", err=True)

    if problems:
        typer.echo("✗ speccify verify: Drift erkannt:", err=True)
        for p in problems:
            typer.echo(f"    - {p}", err=True)
        raise typer.Exit(code=1)

    typer.echo("✓ speccify verify: Manifest, Lockfile und Output sind konsistent.")
