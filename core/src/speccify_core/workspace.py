"""Workspace-Unterstützung (Phase 3 Stage 5 — Cargo-Stil Root-Lockfile + globale MVS).

Ein **Workspace-Root** ist ein `speccify.yaml` mit einem `workspaces:`-Feld
(Glob-Liste relativ zum Root). Member sind eigenständige `speccify.yaml`-Dateien
mit eigenen `targets:` + `dependencies:`. Die Root-Datei darf zusätzlich
`dependencies` + `targets` haben (Root-als-Member), muss aber nicht (reiner
Workspace-Root).

**Globale MVS** (Stage-0-Decision): Constraints aller Member werden gemeinsam
aufgelöst → eine Version pro Spec für den gesamten Workspace. Drift in einem
Member schlägt im `verify` daher zuverlässig fehl, weil das eine Lockfile am
Root liegt. Pro Constraint speichert der Resolver den Member-Pfad als
`source=<member-relpath>`-Trace; `RangeConflictError` aus Phase 1a meldet bei
Konflikt den Quell-Member.

**Targets-Aggregation**: `Workspace.aggregated_targets()` ist die deduplizierte,
sortierte Union aller Member-`targets` (plus Root-Targets, falls vorhanden).
Lockfile-`targets` bekommt diese Union → Cross-Product mit Resolutionen wie in
Stage 1b.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from speccify_core.manifest import ManifestError, ProjectManifest

MANIFEST_FILENAME = "speccify.yaml"


class WorkspaceError(Exception):
    """Workspace konnte nicht entdeckt oder nicht validiert werden."""


@dataclass(frozen=True)
class WorkspaceMember:
    """Ein einzelnes Member-Manifest innerhalb eines Workspace.

    `relative_path` ist der POSIX-Pfad vom Workspace-Root zum Member-Manifest
    (z. B. `packages/ui/speccify.yaml`). Wird als `source`-Trace im Resolver
    benutzt.
    """

    relative_path: str
    manifest: ProjectManifest


@dataclass(frozen=True)
class Workspace:
    """Ein aufgelöster Workspace (Root + entdeckte Member).

    Wird via :meth:`load` aus einem Root-Manifest erzeugt; die Member-Liste
    ist deterministisch nach `relative_path` sortiert.
    """

    root_dir: Path
    root_manifest: ProjectManifest
    members: tuple[WorkspaceMember, ...]

    @classmethod
    def load(cls, root_dir: str | Path) -> Workspace:
        """Lädt das Root-Manifest und entdeckt alle Member via `workspaces:`-Globs.

        Wirft :class:`WorkspaceError`, wenn das Root-Manifest kein `workspaces:`-Feld
        hat, kein Glob auflöst oder ein Member-Verzeichnis kein `speccify.yaml`
        enthält.
        """
        root = Path(root_dir).resolve()
        root_manifest_path = root / MANIFEST_FILENAME
        if not root_manifest_path.is_file():
            raise WorkspaceError(f"Kein {MANIFEST_FILENAME} in {root} gefunden.")
        try:
            root_manifest = ProjectManifest.load(root_manifest_path)
        except ManifestError as exc:
            raise WorkspaceError(f"Workspace-Root-Manifest ungültig: {exc}") from exc

        if not root_manifest.is_workspace_root:
            raise WorkspaceError(
                f"Manifest {root_manifest_path} hat kein `workspaces:`-Feld — kein Workspace-Root."
            )

        seen: set[Path] = set()
        members: list[WorkspaceMember] = []
        for pattern in root_manifest.workspaces:
            matches = sorted(root.glob(pattern))
            if not matches:
                raise WorkspaceError(
                    f"Workspace-Glob '{pattern}' (in {root_manifest_path}) "
                    f"matched keine Member-Verzeichnisse."
                )
            for member_dir in matches:
                if not member_dir.is_dir():
                    continue
                if member_dir.resolve() == root:
                    # Root als eigener Member via Glob — überspringen, kommt via
                    # `include_root_as_member()` ins Spiel.
                    continue
                if member_dir.resolve() in seen:
                    continue
                member_manifest_path = member_dir / MANIFEST_FILENAME
                if not member_manifest_path.is_file():
                    raise WorkspaceError(
                        f"Workspace-Member {member_dir} hat kein {MANIFEST_FILENAME}."
                    )
                try:
                    member_manifest = ProjectManifest.load(member_manifest_path)
                except ManifestError as exc:
                    raise WorkspaceError(
                        f"Member-Manifest {member_manifest_path} ungültig: {exc}"
                    ) from exc
                if member_manifest.is_workspace_root:
                    raise WorkspaceError(
                        f"Member-Manifest {member_manifest_path} ist selbst ein "
                        f"Workspace-Root — verschachtelte Workspaces werden nicht unterstützt."
                    )
                seen.add(member_dir.resolve())
                relpath = member_manifest_path.relative_to(root).as_posix()
                members.append(WorkspaceMember(relative_path=relpath, manifest=member_manifest))

        members.sort(key=lambda m: m.relative_path)
        return cls(root_dir=root, root_manifest=root_manifest, members=tuple(members))

    def aggregated_targets(self) -> tuple[str, ...]:
        """Deduplizierte, sortierte Union aller Member-Targets (plus Root-Targets)."""
        union: set[str] = set(self.root_manifest.targets)
        for member in self.members:
            union.update(member.manifest.targets)
        return tuple(sorted(union))

    def aggregated_dependencies(self) -> dict[str, list[tuple[str, str]]]:
        """Aggregierte Dependency-Constraints aller Member.

        Liefert eine Map ``{spec_id: [(range, source-relpath), ...]}``. Wird vom
        Workspace-Resolver als Eingabe benutzt.
        """
        out: dict[str, list[tuple[str, str]]] = {}
        # Root-Dependencies (falls der Root auch als Member dient) zuerst.
        if self.root_manifest.dependencies:
            for spec_id, raw_range in self.root_manifest.dependencies.items():
                out.setdefault(spec_id, []).append((raw_range, "<root>"))
        for member in self.members:
            for spec_id, raw_range in member.manifest.dependencies.items():
                out.setdefault(spec_id, []).append((raw_range, member.relative_path))
        return out
