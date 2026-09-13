"""`speccify verify`: does the lockfile still describe reality?"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import typer
from speccify_core import (
    Lockfile,
    LockfileError,
    RegistryError,
    Resolver,
    ResolverError,
    Version,
    bundle_sha256,
)

from speccify_cli.commands._context import ProjectContext, fetch_bundle
from speccify_cli.commands import expand as expand_module
from speccify_cli.commands.expand import (
    Expansions,
    ExpansionStatus,
    expansion_status,
    expansions_path,
)

TOOL_MISSING = "missing"
TOOL_UNVERIFIED = "unverified"
TOOL_VERIFIED = "verified"


@dataclass
class VerifyReport:
    """One verify result for every adapter (Spec 010).

    `ok` keeps its meaning: lockfile, manifest, bundles and the expanded skills
    agree — no drift, nothing recorded that is gone. `ready` goes further: `ok`
    *and* every recorded tool has an implementation for `platform` that passed
    its examples. Tools are listed individually so a client can tell a missing
    implementation from an unverified one.
    """

    ok: bool
    ready: bool
    platform: str
    problems: list[str] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def tools_to_implement(self) -> list[str]:
        return [t["name"] for t in self.tools if t["state"] == TOOL_MISSING]

    @property
    def tools_to_verify(self) -> list[str]:
        return [t["name"] for t in self.tools if t["state"] == TOOL_UNVERIFIED]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "ready": self.ready,
            "platform": self.platform,
            "problems": list(self.problems),
            "tools": [dict(t) for t in self.tools],
            "notes": list(self.notes),
            "error": self.error,
        }


def run_verify_report(
    project_dir: Path,
    *,
    library_override: Path | None = None,
    offline: bool = False,
    platform: str | None = None,
) -> VerifyReport:
    """The shared computation behind `speccify verify --json` and the MCP tool."""
    # Über das Modul, nicht per Name: Tests pinnen `expand.current_platform`.
    platform = platform or expand_module.current_platform()
    try:
        problems, status = run_verify_with_status(
            project_dir, library_override=library_override, offline=offline, platform=platform
        )
    except (LockfileError, FileNotFoundError) as exc:
        return VerifyReport(ok=False, ready=False, platform=platform, error=str(exc))
    tools: list[dict[str, Any]] = []
    try:
        record = Expansions.load(expansions_path(project_dir))
        names = sorted(record.tools)
    except Exception:  # noqa: BLE001 — no record, no tools
        names = []
    for name in names:
        if name in status.tools_to_implement:
            state = TOOL_MISSING
        elif name in status.tools_to_verify:
            state = TOOL_UNVERIFIED
        else:
            state = TOOL_VERIFIED
        tools.append({"name": name, "state": state})
    notes = [
        f"tool '{name}' has no implementation for {platform} yet."
        for name in status.tools_to_implement
    ] + [
        f"tool '{name}' is implemented but not yet checked against its examples."
        for name in status.tools_to_verify
    ]
    ok = not problems
    return VerifyReport(
        ok=ok,
        ready=ok and all(t["state"] == TOOL_VERIFIED for t in tools),
        platform=platform,
        problems=problems,
        tools=tools,
        notes=notes,
    )


def run_verify(
    project_dir: Path,
    *,
    library_override: Path | None = None,
    offline: bool = False,
) -> list[str]:
    """Compare manifest, lockfile and the actual bundles; returns problems."""
    problems, _ = run_verify_with_status(
        project_dir, library_override=library_override, offline=offline
    )
    return problems


def run_verify_with_status(
    project_dir: Path,
    *,
    library_override: Path | None = None,
    offline: bool = False,
    platform: str | None = None,
) -> tuple[list[str], ExpansionStatus]:
    """Problems with the lock, plus how the expanded skills under .agent/ relate to it."""
    problems: list[str] = []
    hashes: dict[str, str] = {}
    context = ProjectContext.load(project_dir, library_override=library_override, offline=offline)
    if not context.lockfile_path.is_file():
        return [f"No lockfile in {project_dir}. Run `speccify lock` first."], ExpansionStatus()
    lockfile = Lockfile.load(context.lockfile_path)

    try:
        graph = Resolver(context.libraries).resolve(context.manifest)
    except (ResolverError, RegistryError) as exc:
        return [str(exc)], ExpansionStatus()

    resolved = {r.playbook_id: r for r in graph.resolutions}
    locked = {e.id: e for e in lockfile.entries}
    for playbook_id in sorted(set(locked) - set(resolved)):
        problems.append(f"'{playbook_id}' is in the lockfile but no longer resolved.")
    for playbook_id in sorted(set(resolved) - set(locked)):
        problems.append(f"'{playbook_id}' resolves but is missing from the lockfile.")

    for playbook_id in sorted(set(locked) & set(resolved)):
        entry, resolution = locked[playbook_id], resolved[playbook_id]
        if str(resolution.version) != entry.version:
            problems.append(
                f"{playbook_id}: version drift — lockfile {entry.version}, "
                f"resolved {resolution.version}."
            )
            continue
        try:
            bundle = fetch_bundle(context.libraries, entry.id, Version.parse(entry.version))
        except RegistryError as exc:
            problems.append(str(exc))
            continue
        actual = bundle_sha256(bundle.files)
        hashes[playbook_id] = actual
        if actual != entry.bundle_sha256:
            problems.append(
                f"{playbook_id}@{entry.version}: bundle hash drift — "
                f"lockfile {entry.bundle_sha256}, actual {actual}."
            )
        if entry.source_commit and bundle.source_commit != entry.source_commit:
            problems.append(
                f"{playbook_id}@{entry.version}: commit drift — lockfile "
                f"{entry.source_commit[:12]}, actual {(bundle.source_commit or '?')[:12]}. "
                f"A tag was moved."
            )
    status = expansion_status(project_dir, locked_hashes=hashes, platform=platform)
    problems.extend(status.drift)
    problems.extend(status.missing)
    return problems, status


def verify_command(
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
    library: Path | None = typer.Option(  # noqa: B008
        None, "--library", help="Local playbook library (default: from the manifest)."
    ),
    offline: bool = typer.Option(
        False, "--offline/--no-offline", help="Only read cached git sources, never the network."
    ),
    platform: str | None = typer.Option(
        None, "--platform", help="Judge tool implementations for this platform (default: current)."
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Print the full report as JSON (same fields as the MCP `verify` tool).",
    ),
) -> None:
    """Check that the lockfile still matches the manifest and the actual bundles."""
    report = run_verify_report(
        project_dir, library_override=library, offline=offline, platform=platform
    )
    if as_json:
        typer.echo(json.dumps(report.to_dict(), indent=2))
        raise typer.Exit(code=0 if report.ok else 1)
    if report.error is not None:
        typer.echo(f"x speccify verify failed: {report.error}", err=True)
        raise typer.Exit(code=1)
    if report.problems:
        for problem in report.problems:
            typer.echo(f"x {problem}", err=True)
        typer.echo(f"\n{len(report.problems)} problem(s).", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"ok lockfile, manifest and bundles agree ({report.platform}).")
    for note in report.notes:
        typer.echo(f"   {note}")
    if report.tools and report.ready:
        typer.echo(
            f"   {len(report.tools)} tool(s) implemented and verified for {report.platform}."
        )
