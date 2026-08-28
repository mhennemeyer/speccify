"""`speccify expand`: make normal skills out of locked ones, under `.agent/`.

What `pull` writes is the upstream skill as it is — a cache. What the agent
should read is the skill *for this project*: references resolved to sibling
skills, Speccify metadata gone, tools specified project-wide under
`.agent/tools/`, and a section at the end for what is specific here.

`expand` is idempotent and safe to re-run:

* A skill whose upstream hash has not changed is left alone.
* One whose upstream changed is regenerated — upstream part replaced, the
  `## In this project` section carried over as it was.
* Tool specs are refreshed; tool *implementations* (`macos.sh`, `windows.ps1`,
  …) are never touched, because they were written here, not upstream.

The output is the agent's to-do list: which tools need an implementation for
this platform, which placeholders the upstream author left to fill in.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import typer
from speccify_core import (
    Lockfile,
    LockfileError,
    RegistryError,
    Version,
    bundle_sha256,
    parse_uses_entry,
)
from speccify_core.expansion import (
    AGENT_DIR,
    EXPANSIONS_FILENAME,
    IMPLEMENTED,
    SKILLS_DIR,
    VERIFIED,
    Expansions,
    SkillRecord,
    ToolRecord,
    current_platform,
    expand_skill,
    implementation_for,
    sha256_text,
)
from speccify_core.skill import SKILL_FILENAME
from speccify_core.tool import TOOL_FILENAME, TOOLS_DIR

from speccify_cli.commands._context import ProjectContext, fetch_bundle

SPECCIFY_DIR = "speccify"


def agent_root(project_dir: Path) -> Path:
    return project_dir / AGENT_DIR


def expansions_path(project_dir: Path) -> Path:
    return agent_root(project_dir) / SPECCIFY_DIR / EXPANSIONS_FILENAME


@dataclass(frozen=True)
class SkillOutcome:
    name: str
    action: str  # created | updated | unchanged
    tools_to_implement: tuple[str, ...]
    placeholders: tuple[str, ...]
    via: str | None = None  # the skill that pulled this one in, if not requested


@dataclass(frozen=True)
class ExpandReport:
    platform: str
    outcomes: list[SkillOutcome] = field(default_factory=list)

    @property
    def tools_to_implement(self) -> list[str]:
        seen: list[str] = []
        for outcome in self.outcomes:
            for tool in outcome.tools_to_implement:
                if tool not in seen:
                    seen.append(tool)
        return seen


def _resolve_reference(reference: str, locked: Mapping[str, object]) -> str:
    """Volle Id zu einer Referenz — auch zum **Kurznamen** eines gelockten Skills.

    `speccify expand macos-notarize-tauri` soll reichen, wenn das Lockfile
    genau einen Skill dieses Namens kennt (`@scope/name` oder
    `git+…#pfad/name`). Eine volle Id geht unverändert durch; ein
    mehrdeutiger Kurzname ist ein Fehler, kein Raten.
    """
    if reference.startswith(("@", "git+")):
        return parse_uses_entry(reference)[0]
    matches = [sid for sid in locked if sid.rstrip("/").rsplit("/", 1)[-1] == reference]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise RegistryError(
            f"'{reference}' is not in the lockfile. Add it to speccify.yaml "
            f"and run `speccify lock`."
        )
    raise RegistryError(
        f"'{reference}' is ambiguous in the lockfile: {', '.join(sorted(matches))}. "
        f"Use the full id."
    )


def run_expand(
    project_dir: Path,
    references: list[str] | None = None,
    *,
    library_override: Path | None = None,
    offline: bool = False,
    platform: str | None = None,
    today: date | None = None,
) -> ExpandReport:
    """Expand the named skills (default: every manifest dependency) and what they use."""
    platform = platform or current_platform()
    context = ProjectContext.load(project_dir, library_override=library_override, offline=offline)
    if not context.lockfile_path.is_file():
        raise LockfileError(f"No lockfile in {project_dir}. Run `speccify lock` first.")
    lockfile = Lockfile.load(context.lockfile_path)
    locked = {entry.id: entry for entry in lockfile.entries}

    requested = (
        [_resolve_reference(ref, locked) for ref in references]
        if references
        else list(context.manifest.dependencies)
    )
    for skill_id in requested:
        if skill_id not in locked:
            raise RegistryError(
                f"'{skill_id}' is not in the lockfile. Add it to {context.manifest_path.name} "
                f"and run `speccify lock`."
            )

    root = agent_root(project_dir)
    record = Expansions.load(expansions_path(project_dir))
    skills = dict(record.skills)
    tools = dict(record.tools)
    report = ExpandReport(platform=platform)

    # Walk the `uses` graph from the requested skills; each skill once.
    queue: list[tuple[str, str | None]] = [(sid, None) for sid in requested]
    done: set[str] = set()
    while queue:
        skill_id, via = queue.pop(0)
        if skill_id in done:
            continue
        done.add(skill_id)
        entry = locked[skill_id]
        bundle = fetch_bundle(context.libraries, entry.id, Version.parse(entry.version))
        skill = bundle.skill()
        actual = bundle_sha256(bundle.files)

        sibling_names = {}
        for used in skill.uses:
            used_id = parse_uses_entry(used)[0]
            if used_id not in locked:
                raise RegistryError(
                    f"{skill_id} uses '{used_id}', which is not in the lockfile. "
                    f"Run `speccify lock` again."
                )
            sibling_names[used] = used_id.rsplit("/", 1)[-1]
            queue.append((used_id, skill.name))

        skill_dir = root / SKILLS_DIR / skill.name
        skill_file = skill_dir / SKILL_FILENAME
        previous = skills.get(skill.name)
        existing = skill_file.read_text(encoding="utf-8") if skill_file.is_file() else None
        if previous and previous.bundle_sha256 == actual and existing is not None:
            action = "unchanged"
        else:
            action = "updated" if existing is not None else "created"

        expanded = expand_skill(
            skill, bundle.files, sibling_names=sibling_names, existing_markdown=existing
        )
        if action != "unchanged":
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_file.write_text(expanded.skill_markdown, encoding="utf-8")
            # Everything that is neither the skill nor a tool travels with the skill.
            for relative, data in sorted(bundle.files.items()):
                if relative == SKILL_FILENAME or relative.startswith(f"{TOOLS_DIR}/"):
                    continue
                target = skill_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

        # Tools are project-wide. Specs are refreshed; implementations are ours.
        to_implement: list[str] = []
        for tool_name in expanded.tool_names:
            tool_dir = root / TOOLS_DIR / tool_name
            tool_dir.mkdir(parents=True, exist_ok=True)
            spec_bytes = b""
            for relative, data in expanded.tool_files.items():
                if not relative.startswith(f"{TOOLS_DIR}/{tool_name}/"):
                    continue
                filename = relative.split("/", 2)[2]
                if filename == TOOL_FILENAME:
                    spec_bytes = data
                target = tool_dir / filename
                if target.exists() and filename != TOOL_FILENAME:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            known = tools.get(tool_name)
            platforms = dict(known.platforms) if known else {}
            spec_sha = sha256_text(spec_bytes)
            if known and known.spec_sha256 != spec_sha:
                # The contract changed; what was verified against the old one is not
                # verified against this one.
                platforms = {
                    p: ({**info, "status": IMPLEMENTED} if info.get("status") == VERIFIED else info)
                    for p, info in platforms.items()
                }
                for info in platforms.values():
                    info.pop("checked", None)
            implementation = implementation_for(tool_dir, platform)
            if implementation is not None and platform not in platforms:
                platforms[platform] = {"status": IMPLEMENTED, "file": implementation.name}
            if implementation is None:
                to_implement.append(tool_name)
            from_skills = tuple(sorted({*(known.from_skills if known else ()), skill.name}))
            tools[tool_name] = ToolRecord(
                from_skills=from_skills, spec_sha256=spec_sha, platforms=platforms
            )

        stamp = (today or date.today()).isoformat()
        skills[skill.name] = SkillRecord(
            source=entry.id,
            version=entry.version,
            bundle_sha256=actual,
            expanded=previous.expanded if previous and action == "unchanged" else stamp,
            requested=via is None or bool(previous and previous.requested),
            tools=expanded.tool_names,
        )
        report.outcomes.append(
            SkillOutcome(
                name=skill.name,
                action=action,
                tools_to_implement=tuple(to_implement),
                placeholders=expanded.placeholders,
                via=via,
            )
        )

    Expansions(skills=skills, tools=tools).write(expansions_path(project_dir))
    return report


@dataclass(frozen=True)
class ExpansionStatus:
    """How `.agent/` relates to upstream and to this platform."""

    drift: list[str] = field(default_factory=list)  # upstream moved on; re-expand
    missing: list[str] = field(default_factory=list)  # recorded, but gone from disk
    tools_to_implement: list[str] = field(default_factory=list)
    tools_to_verify: list[str] = field(default_factory=list)


def expansion_status(
    project_dir: Path,
    *,
    locked_hashes: dict[str, str],
    platform: str | None = None,
) -> ExpansionStatus:
    """Compare `expansions.yaml` against the lockfile's bundles and the tool directories.

    `locked_hashes` maps skill id → the bundle hash as it is *now*; `verify`
    computes those anyway.
    """
    platform = platform or current_platform()
    record = Expansions.load(expansions_path(project_dir))
    root = agent_root(project_dir)
    status = ExpansionStatus()
    for name, skill in sorted(record.skills.items()):
        if not (root / SKILLS_DIR / name / SKILL_FILENAME).is_file():
            status.missing.append(f"{AGENT_DIR}/{SKILLS_DIR}/{name} is recorded but not on disk.")
            continue
        current = locked_hashes.get(skill.source)
        if current is None:
            status.drift.append(
                f"{name}: expanded from {skill.source}, which is no longer in the lockfile."
            )
        elif current != skill.bundle_sha256:
            status.drift.append(
                f"{name}: upstream {skill.source} changed since it was expanded on "
                f"{skill.expanded} — run `speccify expand` to refresh the upstream part."
            )
    for name, tool in sorted(record.tools.items()):
        tool_dir = root / TOOLS_DIR / name
        if implementation_for(tool_dir, platform) is None:
            status.tools_to_implement.append(name)
        elif tool.status(platform) != VERIFIED:
            status.tools_to_verify.append(name)
    return status


def expand_command(
    references: list[str] = typer.Argument(  # noqa: B008
        None, help="Skill ids to expand (default: every dependency in the manifest)."
    ),
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
    library: Path | None = typer.Option(  # noqa: B008
        None, "--library", help="Local skill library (default: from the manifest)."
    ),
    offline: bool = typer.Option(
        False, "--offline/--no-offline", help="Only read cached git sources, never the network."
    ),
    platform: str | None = typer.Option(
        None, "--platform", help="macos, linux or windows (default: this machine)."
    ),
) -> None:
    """Turn locked skills into normal, project-specific skills under .agent/."""
    try:
        report = run_expand(
            project_dir,
            references or None,
            library_override=library,
            offline=offline,
            platform=platform,
        )
    except (LockfileError, RegistryError, FileNotFoundError, ValueError) as exc:
        typer.echo(f"x speccify expand failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    for outcome in report.outcomes:
        via = f" (used by {outcome.via})" if outcome.via else ""
        typer.echo(f"{outcome.action:9} {AGENT_DIR}/{SKILLS_DIR}/{outcome.name}{via}")
        for placeholder in outcome.placeholders:
            typer.echo(f"          fill in: {placeholder}")
    if report.tools_to_implement:
        typer.echo(f"\nTools to implement for {report.platform}:")
        for tool in report.tools_to_implement:
            typer.echo(
                f"  {AGENT_DIR}/{TOOLS_DIR}/{tool}/{report.platform}.<ext>  "
                f"— contract in {TOOL_FILENAME} beside it"
            )
    typer.echo(
        f"\n{len(report.outcomes)} skill(s) under {AGENT_DIR}/{SKILLS_DIR}/, "
        f"{len(report.tools_to_implement)} tool(s) to implement."
    )
