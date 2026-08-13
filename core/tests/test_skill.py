"""Tests for the `SKILL.md` format.

Two things these pin down, because both are easy to break later:

* Speccify's additions live in `metadata` and stay **out of the agent's way**.
  Only `name` and `description` reach the model at startup; everything else is
  ours to read.
* A skill written by someone else — no numbering, no verify lines, no sources —
  must parse without complaint. Structure is inferred, never demanded.
"""

from __future__ import annotations

from datetime import date

import pytest
from speccify_core.skill import (
    DESCRIPTION_MAX,
    NAME_MAX,
    SkillError,
    parse_skill,
    validate_skill,
)

MINIMAL = """---
name: doing-a-thing
description: Does a thing. Use when a thing needs doing.
---

Just prose.
"""

FULL = """---
name: macos-notarize-tauri
description: Signs and notarizes a Tauri 2 app so it opens without a Gatekeeper warning.
license: MIT
compatibility: Requires Xcode command line tools
metadata:
  speccify.version: "1.0.0"
  speccify.scope: mhennemeyer
  speccify.stack: "tauri, xcode"
  speccify.platforms: macos
  speccify.uses: "@mhennemeyer/apple-developer-id-cert@^1.0"
---

## 1 — Turn on the hardened runtime

Notarization rejects anything without it.

**Verify:** `codesign -d --entitlements -` shows the runtime flag.

## 2 — Submit to notarytool

Wait for the verdict.

## Pitfalls

- Unsigned sidecars pass the build and fail notarization.

## Sources

- [Notarizing macOS software](https://developer.apple.com/a) — retrieved 2026-08-06
- [Customizing the workflow](https://developer.apple.com/b)
"""


def test_minimal_skill_is_valid() -> None:
    """The spec requires exactly two fields. Everything else is optional."""
    skill = parse_skill(MINIMAL)
    assert skill.name == "doing-a-thing"
    assert validate_skill(skill) == []
    # Nothing inferred, nothing complained about.
    assert skill.steps == ()
    assert skill.sources == ()
    assert skill.uses == ()


def test_speccify_additions_live_in_metadata() -> None:
    skill = parse_skill(FULL)
    assert skill.version == "1.0.0"
    assert skill.qualified_id == "@mhennemeyer/macos-notarize-tauri"
    assert skill.stack == ("tauri", "xcode")
    assert skill.platforms == ("macos",)
    assert skill.uses == ("@mhennemeyer/apple-developer-id-cert@^1.0",)


def test_steps_are_inferred_and_reserved_sections_are_not_steps() -> None:
    skill = parse_skill(FULL)
    assert [(s.number, s.title) for s in skill.steps] == [
        (1, "Turn on the hardened runtime"),
        (2, "Submit to notarytool"),
    ]
    assert skill.steps[0].verify is not None
    assert skill.steps[1].verify is None


def test_sources_carry_their_retrieval_date() -> None:
    skill = parse_skill(FULL)
    first, second = skill.sources
    assert first.retrieved == "2026-08-06"
    assert first.age_days(today=date(2026, 8, 13)) == 7
    # A source without a date parses; the gap is a finding for `check`, not here.
    assert second.retrieved is None
    assert second.age_days(today=date(2026, 8, 13)) is None


def test_a_foreign_skill_parses_without_conventions() -> None:
    """Anything from another author must not need Speccify's habits."""
    foreign = """---
name: pdf-processing
description: Extracts text from PDFs. Use when working with PDF files.
---

# PDF Processing

## Quick start

Use pdfplumber.

## Advanced features

See FORMS.md.
"""
    skill = parse_skill(foreign)
    assert validate_skill(skill) == []
    assert [s.title for s in skill.steps] == ["Quick start", "Advanced features"]
    assert all(s.number is None and s.verify is None for s in skill.steps)


@pytest.mark.parametrize(
    ("name", "why"),
    [
        ("PDF-Processing", "uppercase"),
        ("-leading", "leading hyphen"),
        ("trailing-", "trailing hyphen"),
        ("double--hyphen", "consecutive hyphens"),
        ("claude-helper", "reserved word"),
        ("anthropic-tools", "reserved word"),
        ("x" * (NAME_MAX + 1), "too long"),
    ],
)
def test_invalid_names_are_rejected(name: str, why: str) -> None:
    skill = parse_skill(f"---\nname: {name}\ndescription: Something. Use when.\n---\n")
    assert validate_skill(skill), f"{why} should be rejected"


def test_description_is_required_and_bounded() -> None:
    empty = parse_skill("---\nname: a-skill\ndescription: ''\n---\n")
    assert any(i.path == "description" for i in validate_skill(empty))

    long = parse_skill(f"---\nname: a-skill\ndescription: {'x' * (DESCRIPTION_MAX + 1)}\n---\n")
    assert any("maximum" in i.message for i in validate_skill(long))


def test_metadata_must_not_nest() -> None:
    """The spec allows string to string only — nested data would break other tools."""
    nested = """---
name: a-skill
description: Something. Use when something.
metadata:
  speccify.uses:
    - "@me/one"
    - "@me/two"
---
"""
    skill = parse_skill(nested)
    issues = validate_skill(skill)
    assert [i.path for i in issues] == ["metadata.speccify.uses"]
    assert "strings only" in issues[0].message
    # The unusable value is dropped rather than stringified into something that
    # looks like data: `str(["@me/one"])` would parse back as one odd entry.
    assert skill.uses == ()


def test_yaml_scalars_are_coerced_rather_than_refused() -> None:
    """`version: 1.0` is a float in YAML; refusing it would be pedantry."""
    skill = parse_skill(
        "---\nname: a-skill\ndescription: Something. Use when.\n"
        "metadata:\n  speccify.version: 1.0\n---\n"
    )
    assert skill.version == "1.0"
    assert validate_skill(skill) == []


def test_missing_frontmatter_is_an_error() -> None:
    with pytest.raises(SkillError, match="frontmatter"):
        parse_skill("# Just markdown\n")


def test_bundle_must_contain_skill_md() -> None:
    skill = parse_skill(MINIMAL)
    assert validate_skill(skill, bundle_files={"README.md"})
    assert validate_skill(skill, bundle_files={"SKILL.md"}) == []


def test_source_url_may_contain_parentheses() -> None:
    """Apple's Swift documentation URLs end in `sync()`.

    A naive `[^)]+` swallows the link at the first bracket and then never sees
    the retrieval date behind it — the source silently loses its age.
    """
    text = (
        "---\nname: a-skill\ndescription: Something. Use when something.\n---\n\n"
        "## Sources\n\n"
        "- [AppStore.sync()](https://developer.apple.com/documentation/storekit/appstore/sync())"
        " — retrieved 2026-08-06\n"
    )
    (source,) = parse_skill(text).sources
    assert source.url.endswith("/appstore/sync()")
    assert source.retrieved == "2026-08-06"
