#!/usr/bin/env python3
"""Spec 073: list `t("…")` keys in apps/desktop/src that have no English entry,
and English entries whose placeholders do not match the German key.

    python3 scripts/check_i18n.py            # report, exit 1 when something is missing
    python3 scripts/check_i18n.py --allow-code   # ignore command/path-like keys
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "apps" / "desktop" / "src"
EN = ROOT / "i18n" / "en.ts"
CODE_LIKE = re.compile(r"^[\w./~<>@:+ -]*(install|cargo|pnpm|uv |git |dotagent|speccify |\.md|\.rs|\.tsx|\.toml|\.json|/)[\w./~<>@:+ -]*$")


def keys_in_source() -> dict[str, str]:
    found: dict[str, str] = {}
    for path in sorted(ROOT.rglob("*.ts*")):
        if "i18n" in path.parts or path.name.endswith(".d.ts"):
            continue
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r'\bt\(\s*("(?:[^"\\]|\\.)*")', text):
            found.setdefault(json.loads(match.group(1)), str(path.relative_to(ROOT)))
        for match in re.finditer(r'\bplural\(\s*[^,]+,\s*("(?:[^"\\]|\\.)*")\s*,\s*("(?:[^"\\]|\\.)*")', text):
            for group in (match.group(1), match.group(2)):
                found.setdefault(json.loads(group), str(path.relative_to(ROOT)))
    return found


def english() -> dict[str, str]:
    text = EN.read_text(encoding="utf-8")
    entries: dict[str, str] = {}
    for match in re.finditer(r'^\s*("(?:[^"\\]|\\.)*")\s*:\s*("(?:[^"\\]|\\.)*")\s*,?\s*$', text, re.M):
        entries[json.loads(match.group(1))] = json.loads(match.group(2))
    return entries


def main() -> int:
    allow_code = "--allow-code" in sys.argv
    source = keys_in_source()
    en = english()
    missing = [k for k in source if k not in en and not (allow_code and CODE_LIKE.match(k))]
    bad_placeholders = [
        k for k, v in en.items() if set(re.findall(r"\{(\w+)\}", k)) != set(re.findall(r"\{(\w+)\}", v))
    ]
    # Labels held in plain constants (tab names, presets, status maps) are
    # translated at the render site as t(label); count them as used.
    literals = set()
    for path in ROOT.rglob("*.ts*"):
        if "i18n" in path.parts or path.name.endswith(".d.ts"):
            continue
        for match in re.finditer(r'"((?:[^"\\\n]|\\.)*)"', path.read_text(encoding="utf-8")):
            try:
                literals.add(json.loads('"' + match.group(1) + '"'))
            except ValueError:
                pass
    unused = [k for k in en if k not in source and k not in literals]
    print(f"keys in source: {len(source)} · english entries: {len(en)} · missing: {len(missing)} · unused: {len(unused)}")
    for k in missing:
        print(f"  missing  {source[k]}: {k}")
    for k in bad_placeholders:
        print(f"  placeholders differ: {k}")
    for k in unused:
        print(f"  unused   {k}")
    return 1 if missing or bad_placeholders else 0


if __name__ == "__main__":
    raise SystemExit(main())
