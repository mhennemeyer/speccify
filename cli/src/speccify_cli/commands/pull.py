"""`speccify pull`: rendert Specs aus dem Lockfile und schreibt Output-Hashes zurück.

Phase 1b Step 5b:
- Ruft den Codegen-Dispatcher `render_for_target(spec, target, llm_client=...)`
  statt direkt den Stub-Adapter. Für `target == "react"` wird ein
  `ReplayCacheClient` gegen den eingecheckten Replay-Cache eingespeist
  (Default-Pfad in `_llm_client.py`).
- Neue Flags: `--offline/--no-offline` (Default: `--offline`, kein Live-LLM-Call)
  und `--cache-dir` (überschreibt `SPECCIFY_CACHE_DIR` und den Repo-Default).
- Schreibt pro Spec einen `LlmGeneratorPin` ins Lockfile (`provider`,
  `model`, `prompt_version`, optional `seed`, `cache_key=sha256:<digest>`),
  zusätzlich zu `generated_files_sha256`.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import typer
from speccify_core import (
    CacheMissError,
    CodegenError,
    GeneratedFile,
    LlmGeneratorPin,
    LocalRegistry,
    Lockfile,
    LockfileError,
    Workspace,
    WorkspaceError,
    render_for_target,
)
from speccify_core.codegen import react_llm
from speccify_core.manifest import ManifestError, ProjectManifest
from speccify_core.registry import RegistryError, Version

from speccify_cli.commands._llm_client import build_replay_client
from speccify_cli.commands._workspace import (
    LOCKFILE_FILENAME,
    MANIFEST_FILENAME,
    WorkspaceContext,
)

WORKSPACE_OUTPUT_DIRNAME = "speccify_generated"


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".speccify-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _is_workspace_root(project_dir: Path) -> bool:
    """Detection: Manifest mit `workspaces:`-Key ⇒ Workspace-Root."""
    manifest_path = project_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return False
    try:
        manifest = ProjectManifest.load(manifest_path)
    except ManifestError:
        return False
    return manifest.is_workspace_root


def _render_lock_entry_into(
    lockfile: Lockfile,
    entry_id: str,
    target: str,
    out_dir: Path,
    registry: Registry,
    llm_client: object,
) -> Lockfile:
    """Rendert genau einen Lock-Entry (`spec_id`, `target`) in `out_dir` und aktualisiert das Lockfile.

    `out_dir` ist die Wurzel für das Render-Layout (Renderer schreibt seine eigene
    Unterstruktur — z. B. `org/Button.tsx` — relativ dazu).
    """
    matching = [e for e in lockfile.entries if e.id == entry_id and e.target == target]
    if not matching:
        raise LockfileError(
            f"Lockfile enthält keinen Eintrag für {entry_id!r} mit target={target!r}."
        )
    entry = matching[0]
    spec = registry.fetch(entry.id, Version.parse(entry.version))
    rendered = render_for_target(spec, target, llm_client=llm_client)
    generated: list[GeneratedFile] = []
    for rel_path, data in sorted(rendered.files.items()):
        abs_path = out_dir / rel_path
        _atomic_write(abs_path, data)
        digest = hashlib.sha256(data).hexdigest()
        generated.append(GeneratedFile(path=rel_path, sha256=f"sha256:{digest}"))
    updated = lockfile.with_generated_files(entry.id, generated)
    if rendered.cache_key is not None:
        pin = LlmGeneratorPin(
            provider=react_llm.PROVIDER,
            model=rendered.cache_key.model,
            prompt_version=rendered.cache_key.prompt_version,
            cache_key=f"sha256:{rendered.cache_key.digest()}",
            seed=rendered.cache_key.seed,
        )
        updated = updated.with_generator(entry.id, pin)
    return updated


def _run_workspace_pull(
    project_dir: Path,
    registry_override: Path | None,
    *,
    offline: bool,
    cache_dir: Path | None,
) -> Lockfile:
    """Phase 4 Stage 3: Workspace-Pull — iteriert über Members, materialisiert je Member."""
    workspace = Workspace.load(project_dir)
    lockfile_path = project_dir / LOCKFILE_FILENAME
    if not lockfile_path.is_file():
        raise LockfileError(
            f"Kein Lockfile in {project_dir} gefunden. Bitte zuerst `speccify lock` ausführen."
        )
    lockfile = Lockfile.load(lockfile_path)

    if registry_override is not None:
        registry_path = registry_override.resolve()
    else:
        registry_path = workspace.root_manifest.resolved_registry_path()
    registry = LocalRegistry(registry_path)
    llm_client = build_replay_client(offline=offline, cache_dir=cache_dir)

    updated = lockfile
    for member in workspace.members:
        # Per-Member-Output unter `<root>/<member-dir>/speccify_generated/<target>/`
        # (Stage-0-Decision: sichtbar, committable).
        member_dir = (project_dir / member.relative_path).parent
        member_targets = member.manifest.targets
        member_deps = set(member.manifest.dependencies.keys())
        for target in member_targets:
            target_out = member_dir / WORKSPACE_OUTPUT_DIRNAME / target
            target_out.mkdir(parents=True, exist_ok=True)
            # Nur Entries rendern, deren spec_id in den Member-Deps liegt UND deren
            # target matched. Transitive Deps werden nicht pro Member materialisiert
            # (Stage-0-Decision: Members entkoppelt; Aggregation nur in der Resolution).
            relevant = [
                e for e in updated.entries if e.id in member_deps and e.target == target
            ]
            for entry in relevant:
                updated = _render_lock_entry_into(
                    updated,
                    entry.id,
                    target,
                    target_out,
                    registry,
                    llm_client,
                )

    updated.write(lockfile_path)
    return updated


def run_pull(
    project_dir: Path,
    out_dir: Path,
    target_override: str | None = None,
    registry_override: Path | None = None,
    *,
    offline: bool = True,
    cache_dir: Path | None = None,
) -> Lockfile:
    if _is_workspace_root(project_dir):
        if target_override is not None:
            raise LockfileError(
                "--target ist im Workspace-Modus nicht unterstützt — jeder Member liefert "
                "seine eigenen Targets via `targets:` im Member-Manifest."
            )
        return _run_workspace_pull(
            project_dir,
            registry_override,
            offline=offline,
            cache_dir=cache_dir,
        )

    ctx = WorkspaceContext.load(project_dir, registry_override=registry_override)
    if not ctx.lockfile_path.is_file():
        raise LockfileError(
            f"Kein Lockfile in {project_dir} gefunden. Bitte zuerst `speccify lock` ausführen."
        )
    lockfile = Lockfile.load(ctx.lockfile_path)

    target = target_override or lockfile.target
    if target_override is not None and target_override != lockfile.target:
        raise LockfileError(
            f"--target '{target_override}' weicht vom Lockfile-Target '{lockfile.target}' ab. "
            f"Bitte zuerst `speccify lock` mit gewünschtem Target ausführen."
        )

    llm_client = build_replay_client(offline=offline, cache_dir=cache_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    updated = lockfile
    for entry in lockfile.entries:
        updated = _render_lock_entry_into(
            updated,
            entry.id,
            target,
            out_dir,
            ctx.registry,
            llm_client,
        )

    updated.write(ctx.lockfile_path)
    return updated


def pull_command(
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
        help="Ausgabeverzeichnis für gerenderte Dateien.",
    ),
    target: str | None = typer.Option(  # noqa: B008
        None,
        "--target",
        help="Codegen-Target (Default: Target aus Lockfile).",
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
        help="Nur Replay-Cache benutzen (Default). Mit --no-offline würde ein "
        "Live-LLM-Call bei Cache-Miss erlaubt; in 5b nicht verdrahtet.",
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
    """Rendert resolved Specs aus dem Lockfile und aktualisiert Output-Hashes."""
    project = project_dir or Path.cwd()
    try:
        lockfile = run_pull(
            project,
            out_dir=out,
            target_override=target,
            registry_override=registry,
            offline=offline,
            cache_dir=cache_dir,
        )
    except (
        ManifestError,
        RegistryError,
        LockfileError,
        FileNotFoundError,
        CacheMissError,
        CodegenError,
        WorkspaceError,
    ) as exc:
        typer.echo(f"✗ speccify pull fehlgeschlagen: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    files_total = sum(len(e.generated_files_sha256) for e in lockfile.entries)
    typer.echo(
        f"✓ {files_total} Dateien gerendert ({len(lockfile.entries)} Specs) → {out.resolve()}"
    )
