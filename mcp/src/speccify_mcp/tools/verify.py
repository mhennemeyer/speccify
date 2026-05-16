"""`verify`-Tool: Drift-Check zwischen Manifest, Lockfile und Disk-Output.

Spiegelt `speccify verify` 1:1 — gibt strukturierte Problemliste zurück,
löst nicht aus (auch wenn `ok=False`). Der MCP-Aufruf signalisiert
Fehler über `ok`/`problems`, damit Agents Diagnose-Text bekommen.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from speccify_core import (
    CacheMissError,
    CodegenError,
    LlmGeneratorPin,
    Lockfile,
    RegistryError,
    Resolver,
    Version,
    render_for_target,
)

from ._workspace import WorkspaceContext, build_replay_client


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    problems: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "problems": list(self.problems)}


def run_verify(
    project_root: Path,
    out_dir: Path,
    *,
    registry_path: Path | None = None,
    offline: bool = True,
    cache_dir: Path | None = None,
) -> VerifyResult:
    """Prüft Manifest/Lockfile/Disk-Konsistenz. Leere `problems` → grün."""
    problems: list[str] = []

    ctx = WorkspaceContext.load(project_root, registry_override=registry_path)
    if not ctx.lockfile_path.is_file():
        return VerifyResult(
            ok=False,
            problems=[f"Kein Lockfile in {project_root} (bitte zuerst `lock` aufrufen)."],
        )
    lockfile = Lockfile.load(ctx.lockfile_path)

    # 1) Re-resolve und vergleiche.
    graph = Resolver(ctx.registry).resolve(ctx.manifest)
    if graph.target != lockfile.target:
        problems.append(f"Target-Drift: Manifest={graph.target!r}, Lockfile={lockfile.target!r}.")

    resolved_by_id = {r.spec_id: r for r in graph.resolutions}
    locked_by_id = {e.id: e for e in lockfile.entries}

    for spec_id in sorted(set(locked_by_id) - set(resolved_by_id)):
        problems.append(f"Spec '{spec_id}' im Lockfile, aber nicht mehr aufgelöst.")
    for spec_id in sorted(set(resolved_by_id) - set(locked_by_id)):
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
                f"Lockfile={entry.sha256}, neu={resolution.spec_sha256}."
            )

    # 2) Re-render + Pin-/Hash-Drift.
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

        if isinstance(entry.generator, LlmGeneratorPin):
            if rendered.cache_key is None:
                problems.append(
                    f"Generator-Pin-Drift für {entry.id}: Lockfile=llm, Re-Render=template."
                )
            else:
                expected_cache_key = f"sha256:{rendered.cache_key.digest()}"
                if entry.generator.model != rendered.cache_key.model:
                    problems.append(
                        f"Modell-Drift für {entry.id}: "
                        f"Lockfile={entry.generator.model}, "
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
                        f"Seed-Drift für {entry.id}: "
                        f"Lockfile={entry.generator.seed}, "
                        f"Re-Render={rendered.cache_key.seed}."
                    )
                if entry.generator.cache_key != expected_cache_key:
                    problems.append(
                        f"Cache-Key-Drift für {entry.id}: "
                        f"Lockfile={entry.generator.cache_key}, "
                        f"Re-Render={expected_cache_key}."
                    )

        expected = {f.path: f.sha256 for f in entry.generated_files_sha256}
        if not expected:
            problems.append(
                f"Spec {entry.id}@{entry.version} hat keine "
                f"`generated_files_sha256` (bitte `pull` aufrufen)."
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

            on_disk = out_dir / path
            if not on_disk.is_file():
                problems.append(f"Output-Datei fehlt auf Disk: {on_disk}.")
                continue
            disk_digest = f"sha256:{hashlib.sha256(on_disk.read_bytes()).hexdigest()}"
            if disk_digest != expected[path]:
                problems.append(
                    f"Disk-Drift für {on_disk}: Lockfile={expected[path]}, Datei={disk_digest}."
                )

    return VerifyResult(ok=not problems, problems=problems)
