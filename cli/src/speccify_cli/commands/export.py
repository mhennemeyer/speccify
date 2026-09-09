"""`speccify export`: a project skill goes to a library — the reverse of expand.

A skill that was born here (done three times, with tools written here) is
copied into a library checkout as `<category>/<name>/`: `SKILL.md` without
its `## In this project` section and with an id (`speccify.version`,
`speccify.scope`), each tool as its contract plus the local implementation
as `reference.<ext>`, assets alongside. Then the target is checked like any
library skill and the command prints what only a reader can do: the lines
that look project-specific and need a placeholder or a cut.

Nothing is committed. The library is a git checkout the user (or the app's
git tab, or the agent) commits and pushes; afterwards `speccify add` +
`expand` in the project record the origin so drift shows up later.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer
from speccify_core.expansion import SKILLS_DIR, Expansions, current_platform
from speccify_core.export import (
    REFERENCE_STEM,
    Suspect,
    find_suspects,
    generalise_skill,
    referenced_tools,
)
from speccify_core.skill import SKILL_FILENAME, SkillError, parse_skill
from speccify_core.skill_check import check_skill_directory, find_skills
from speccify_core.tool import TOOL_FILENAME, TOOLS_DIR

from speccify_cli.commands.expand import agent_root, expansions_path

DEFAULT_CATEGORY = "skills"


@dataclass(frozen=True)
class ExportReport:
    target: Path
    skill_id: str
    version: str
    written: tuple[str, ...]
    left_alone: tuple[str, ...]
    tools: tuple[str, ...]
    placeholders: tuple[str, ...]
    suspects: tuple[Suspect, ...]
    findings: tuple  # `Finding`s from the library-side check
    library: Path

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.is_error)


def _files_under(directory: Path) -> dict[str, bytes]:
    """Every file below `directory`, relative POSIX path → bytes; dot-files skipped."""
    files: dict[str, bytes] = {}
    if not directory.is_dir():
        return files
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(directory)
        if any(part.startswith(".") for part in relative.parts):
            continue
        files[relative.as_posix()] = path.read_bytes()
    return files


def _bump_patch(version: str | None) -> str:
    parts = (version or "").split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
    return "1.0.0"


def _library_scope(library: Path) -> str | None:
    """The scope the library's skills already use — the export joins that namespace."""
    for directory in sorted(find_skills(library)):
        try:
            scope = parse_skill((directory / SKILL_FILENAME).read_text(encoding="utf-8")).scope
        except (OSError, SkillError):
            continue
        if scope:
            return scope
    return None


def run_export(
    project_dir: Path,
    name: str,
    *,
    library: Path,
    category: str = DEFAULT_CATEGORY,
    version: str | None = None,
    scope: str | None = None,
    force: bool = False,
    platform: str | None = None,
) -> ExportReport:
    root = agent_root(project_dir)
    skill_dir = root / SKILLS_DIR / name
    skill_file = skill_dir / SKILL_FILENAME
    if not skill_file.is_file():
        raise SkillError(f"No skill '{name}' under {root / SKILLS_DIR}.")
    markdown = skill_file.read_text(encoding="utf-8")

    library = library.expanduser().resolve()
    if not library.is_dir():
        raise SkillError(
            f"{library} is not a directory — add the source in the app (it clones the repo) "
            f"or clone it yourself first."
        )
    target = library / category.strip("/") / name if category.strip("/") else library / name
    existing = target / SKILL_FILENAME
    if existing.is_file() and not force:
        raise SkillError(
            f"{existing} exists. Pass --force to replace {SKILL_FILENAME}, {TOOL_FILENAME} and "
            f"{REFERENCE_STEM}.* there (fixtures and other files are left alone)."
        )

    record = Expansions.load(expansions_path(project_dir))
    origin = record.skills.get(name)
    tool_names = list(referenced_tools(markdown))
    for tool_name, tool in sorted(record.tools.items()):
        if name in tool.from_skills and tool_name not in tool_names:
            tool_names.append(tool_name)
    tools = {
        tool_name: _files_under(root / TOOLS_DIR / tool_name)
        for tool_name in tool_names
        if (root / TOOLS_DIR / tool_name / TOOL_FILENAME).is_file()
    }

    if scope is None:
        if origin and origin.source.startswith("@"):
            scope = origin.source[1:].split("/", 1)[0]
        else:
            scope = _library_scope(library)
    if version is None:
        if existing.is_file():
            version = _bump_patch(parse_skill(existing.read_text(encoding="utf-8")).version)
        elif origin:
            version = _bump_patch(origin.version)
        else:
            version = "1.0.0"

    siblings = tuple(
        sorted(
            p.name
            for p in (root / SKILLS_DIR).iterdir()
            if p.is_dir() and p.name != name and (p / SKILL_FILENAME).is_file()
        )
    )
    exported = generalise_skill(
        markdown,
        version=version,
        scope=scope,
        tools=tools,
        platform=platform or current_platform(),
        sibling_skills=siblings,
    )
    files = dict(exported.files)
    # Assets beside the skill (assets/, scripts/, references/) travel with it.
    for relative, data in _files_under(skill_dir).items():
        if relative != SKILL_FILENAME:
            files.setdefault(relative, data)

    written: list[str] = []
    left_alone: list[str] = []
    for relative, data in sorted(files.items()):
        destination = target / relative
        replaceable = (
            relative == SKILL_FILENAME
            or relative.endswith(f"/{TOOL_FILENAME}")
            or destination.stem == REFERENCE_STEM
        )
        if destination.exists() and not replaceable:
            left_alone.append(relative)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        written.append(relative)

    skill_id = f"@{scope}/{name}" if scope else name
    return ExportReport(
        target=target,
        skill_id=skill_id,
        version=version,
        written=tuple(written),
        left_alone=tuple(left_alone),
        tools=exported.tools,
        placeholders=exported.placeholders,
        suspects=find_suspects(files, sibling_skills=siblings),
        findings=tuple(check_skill_directory(target)),
        library=library,
    )


def export_command(
    name: str = typer.Argument(..., help="Skill under .agent/skills/ to export."),
    library: Path = typer.Option(  # noqa: B008
        ..., "--to", help="Library checkout or folder to export into (a Speccify source)."
    ),
    category: str = typer.Option(
        DEFAULT_CATEGORY,
        "--category",
        help="Folder inside the library; the source browser shows folders as categories.",
    ),
    version: str | None = typer.Option(
        None, "--version", help="metadata.speccify.version (default: 1.0.0, or the next patch)."
    ),
    scope: str | None = typer.Option(
        None,
        "--scope",
        help="metadata.speccify.scope → id @scope/name (default: the library's scope).",
    ),
    force: bool = typer.Option(
        False, "--force", help="Replace SKILL.md, TOOL.md and reference.* if the skill exists."
    ),
    platform: str | None = typer.Option(
        None,
        "--platform",
        help="Whose implementation becomes the reference file (default: this platform).",
    ),
    project_dir: Path = typer.Option(  # noqa: B008
        Path("."), "--project", "-p", help="Project directory (default: current directory)."
    ),
) -> None:
    """Copy a project skill into a library as a general skill — the reverse of expand."""
    try:
        report = run_export(
            project_dir,
            name,
            library=library,
            category=category,
            version=version,
            scope=scope,
            force=force,
            platform=platform,
        )
    except SkillError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"exported {name} → {report.target}  ({report.skill_id} {report.version})")
    typer.echo(f"  written: {', '.join(report.written)}")
    if report.left_alone:
        typer.echo(f"  left alone (already there): {', '.join(report.left_alone)}")
    if report.tools:
        typer.echo(f"  tools as contracts: {', '.join(report.tools)}")
    if report.placeholders:
        typer.echo(f"  placeholders already in place: {', '.join(report.placeholders)}")
    if report.findings:
        typer.echo("  check:")
        for finding in report.findings:
            typer.echo(f"    {finding.format()}", err=finding.is_error)
    else:
        typer.echo("  check: ok")

    if report.suspects:
        typer.echo("\nReview before you commit — these lines look project-specific:")
        for suspect in report.suspects:
            typer.echo(f"  {suspect.format()}")
        typer.echo(
            "Replace what belongs to this project with a placeholder <like-this>, or cut it."
        )
        if any(s.kind == "skill-ref" for s in report.suspects):
            typer.echo(
                "skill-ref: another skill of this project — export it too and reference it "
                "via metadata.speccify.uses, or inline what this skill needs from it."
            )
    if not report.skill_id.startswith("@"):
        typer.echo(
            "\nNo scope: the skill has no @scope/name id and cannot be added from the library. "
            "Pass --scope or give the library's skills a metadata.speccify.scope.",
            err=True,
        )
    lib = str(report.library)
    typer.echo(
        "\nNext: commit and push in the library, then record the origin here:\n"
        f'  speccify add {report.skill_id} --library "{lib}" && '
        f'speccify expand {name} --library "{lib}"'
    )
    if report.errors:
        raise typer.Exit(code=1)
