"""`speccify conformance` — Phase 3 Stage 4 (MVP: `static-validate`-Backend).

Pro `(spec, target)`-Paar im Lockfile wird die Spec aus dem Registry geladen,
über den ReplayCache re-rendered, gegen das Lockfile auf Hash-Drift geprüft
und der Target-Validator (`validate_tsx` / `validate_swift` / `validate_ts`)
explizit erneut aufgerufen. Backend-Plugin-Slot für Phase-4-Build-Smoke /
Visual-Regression ist im `core.conformance.ConformanceBackend`-Protocol
vorhanden.
"""

from __future__ import annotations

from pathlib import Path

import typer
from speccify_core import (
    Lockfile,
    LockfileError,
    ResolverError,
    run_conformance,
)
from speccify_core.conformance import format_report
from speccify_core.manifest import ManifestError
from speccify_core.registry import RegistryError

from speccify_cli.commands._llm_client import build_replay_client
from speccify_cli.commands._workspace import WorkspaceContext


def conformance_command(
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
    target: list[str] = typer.Option(  # noqa: B008
        [],
        "--target",
        "-t",
        help="Nur diese Target(s) prüfen (Default: alle Targets des Lockfiles). "
        "Wiederholbar: `-t react -t swiftui`.",
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
    """Prüft pro (Spec, Target), dass Renderer + Validator + Lockfile-Hash stimmen."""
    project = project_dir or Path.cwd()
    try:
        ctx = WorkspaceContext.load(project, registry_override=registry)
        if not ctx.lockfile_path.is_file():
            typer.echo(
                f"✗ speccify conformance: kein Lockfile in {project} "
                f"(bitte `speccify lock` ausführen).",
                err=True,
            )
            raise typer.Exit(code=1)
        lockfile = Lockfile.load(ctx.lockfile_path)
    except (ManifestError, RegistryError, LockfileError, ResolverError, FileNotFoundError) as exc:
        typer.echo(f"✗ speccify conformance fehlgeschlagen: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    llm_client = build_replay_client(offline=offline, cache_dir=cache_dir)
    targets = tuple(target) if target else None
    report = run_conformance(
        lockfile=lockfile,
        registry=ctx.registry,
        llm_client=llm_client,
        targets=targets,
    )

    for line in format_report(report, project_dir=project):
        stream_err = not report.ok
        typer.echo(line, err=stream_err)

    if not report.ok:
        typer.echo(
            f"✗ speccify conformance: {len(report.failures())} von "
            f"{len(report.results)} Pfaden gefailed (Backend: {report.backend}).",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(
        f"✓ speccify conformance: {len(report.results)} Pfade ok (Backend: {report.backend})."
    )
