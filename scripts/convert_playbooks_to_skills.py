"""One-off migration: `playbook.yaml` → `SKILL.md`.

Run once, review the output, delete the script. It exists so the conversion is
reviewable as a diff rather than as ten hand-edits, and so the mapping
decisions are written down somewhere other than a commit message.

    python scripts/convert_playbooks_to_skills.py --dry-run
    python scripts/convert_playbooks_to_skills.py

The one judgement call is `description`. The spec wants **what and when** in a
single field, because that is all an agent sees before deciding to load the
skill. A playbook's `summary` only ever said what; the "when" is synthesised
from `applies_to`, which is precisely the material it was collected for.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = REPO_ROOT / "playbooks"
TARGET_DIR = REPO_ROOT / "skills"
DESCRIPTION_MAX = 1024


def _description(data: dict[str, Any]) -> str:
    """`summary` says what; `applies_to` says when. The spec wants both."""
    summary = " ".join(str(data.get("summary", "")).split())
    applies = data.get("applies_to") or {}
    triggers: list[str] = []

    stack = [str(s) for s in applies.get("stack", ())]
    platforms = [str(p) for p in applies.get("platforms", ())]
    keywords = [str(k) for k in applies.get("keywords", ())]

    context = ""
    if stack and platforms:
        context = f"working with {_join(stack)} on {_join(platforms)}"
    elif stack:
        context = f"working with {_join(stack)}"
    elif platforms:
        context = f"targeting {_join(platforms)}"
    if context:
        triggers.append(context)
    if keywords:
        triggers.append(f"the user mentions {_join(keywords)}")

    when = f" Use when {', or when '.join(triggers)}." if triggers else ""
    description = f"{summary}{when}"
    if len(description) > DESCRIPTION_MAX and len(triggers) > 1:
        # Drop the keyword tail first — it is the least load-bearing part.
        description = f"{summary} Use when {', or when '.join(triggers[:-1])}."
    return description[:DESCRIPTION_MAX].strip()


def _join(items: list[str], conj: str = "or") -> str:
    """`or` for alternatives (keywords), `and` for things that are all needed."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" {conj} " + items[-1]


def _body(data: dict[str, Any]) -> str:
    parts: list[str] = []

    prerequisites = [str(p) for p in data.get("prerequisites", ())]
    if prerequisites:
        parts.append("## Prerequisites\n\n" + "\n".join(f"- {p}" for p in prerequisites))

    sources_by_id = {str(s["id"]): s for s in data.get("sources", ())}

    for index, step in enumerate(data.get("steps", ()), start=1):
        heading = f"## {index} — {step['title']}"
        chunk = [heading, ""]
        if step.get("uses"):
            # A delegated step keeps its place in the sequence; the machine-
            # readable reference lives in `metadata.speccify.uses`.
            chunk.append(f"Covered by the skill `{step['uses']}` — follow that one, then continue.")
        else:
            chunk.append(str(step.get("detail", "")).rstrip())
        if step.get("verify"):
            chunk += ["", f"**Verify:** {step['verify']}"]
        cited = [sources_by_id[s]["title"] for s in step.get("sources", ()) if s in sources_by_id]
        if cited:
            chunk += ["", f"*Source: {_join([str(c) for c in cited])}.*"]
        parts.append("\n".join(chunk).rstrip())

    pitfalls = [" ".join(str(p).split()) for p in data.get("pitfalls", ())]
    if pitfalls:
        parts.append("## Pitfalls\n\n" + "\n".join(f"- {p}" for p in pitfalls))

    acceptance = data.get("acceptance", ())
    if acceptance:
        lines = [
            f"- Given {a.get('given', '?')}, when {a.get('when', '?')}, then {a.get('then', '?')}."
            for a in acceptance
        ]
        parts.append("## Acceptance\n\n" + "\n".join(lines))

    sources = data.get("sources", ())
    if sources:
        lines = []
        for source in sources:
            line = f"- [{source['title']}]({source['url']})"
            if source.get("retrieved"):
                line += f" — retrieved {source['retrieved']}"
            if source.get("note"):
                line += f"\n  {' '.join(str(source['note']).split())}"
            lines.append(line)
        parts.append("## Sources\n\n" + "\n".join(lines))

    return "\n\n".join(parts).rstrip() + "\n"


def _frontmatter(data: dict[str, Any]) -> dict[str, Any]:
    playbook_id = str(data["id"])
    scope, name = playbook_id.lstrip("@").split("/", 1)
    applies = data.get("applies_to") or {}

    metadata: dict[str, str] = {
        "speccify.version": str(data["version"]),
        "speccify.scope": scope,
    }
    for key, values in (("stack", applies.get("stack")), ("platforms", applies.get("platforms"))):
        if values:
            metadata[f"speccify.{key}"] = ", ".join(str(v) for v in values)
    uses = [str(s["uses"]) for s in data.get("steps", ()) if s.get("uses")]
    if uses:
        # `metadata` maps strings to strings — a list has to be one value.
        metadata["speccify.uses"] = ", ".join(dict.fromkeys(uses))

    front: dict[str, Any] = {"name": name, "description": _description(data)}
    if data.get("license"):
        front["license"] = str(data["license"])
    requires = [str(r) for r in applies.get("requires", ())]
    if requires:
        front["compatibility"] = f"Requires {_join(requires, conj='and')}"[:500]
    front["metadata"] = metadata
    return front


def convert(bundle: Path, target_root: Path, *, dry_run: bool) -> Path:
    data = yaml.safe_load((bundle / "playbook.yaml").read_text(encoding="utf-8"))
    front = _frontmatter(data)
    target = target_root / front["name"]

    text = (
        "---\n"
        + yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=88)
        + "---\n\n"
        + _body(data)
    )

    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)
        (target / "SKILL.md").write_text(text, encoding="utf-8")
        source_assets = bundle / "assets"
        if source_assets.is_dir():
            shutil.copytree(source_assets, target / "assets", dirs_exist_ok=True)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", help="convert a single playbook by directory name")
    args = parser.parse_args(argv)

    bundles = sorted(p.parent for p in SOURCE_DIR.rglob("playbook.yaml"))
    if args.only:
        bundles = [b for b in bundles if b.parent.name == args.only or b.name == args.only]
        if not bundles:
            print(f"No playbook matching {args.only!r}.", file=sys.stderr)
            return 1

    for bundle in bundles:
        target = convert(bundle, TARGET_DIR, dry_run=args.dry_run)
        marker = "would write" if args.dry_run else "wrote"
        print(f"{marker} {target.relative_to(REPO_ROOT)}/SKILL.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
