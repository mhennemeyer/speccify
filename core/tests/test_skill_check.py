"""Tests for `speccify check` on skills.

The specification layer is covered by `test_skill.py`. What these pin down is
the layer nobody else checks: the official authoring guidance. `skills-ref
validate` looks at the frontmatter and stops, so a description that never says
*when* to use a skill passes every existing tool and then quietly fails to
trigger for months.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from speccify_core.skill import parse_skill
from speccify_core.skill_check import check_skill, check_skill_directory, find_skills

TODAY = date(2026, 8, 13)


def _skill(description: str = "Does a thing. Use when a thing needs doing.", body: str = "") -> Any:
    return parse_skill(f"---\nname: a-skill\ndescription: {description}\n---\n\n{body}")


def _write(tmp_path: Path, name: str, front: str = "", body: str = "") -> Path:
    directory = tmp_path / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Does a thing. Use when a thing needs doing.\n"
        f"{front}---\n\n{body}",
        encoding="utf-8",
    )
    return directory


# --- Best practice --------------------------------------------------------------


def test_description_without_a_trigger_is_flagged() -> None:
    """It is the only thing the agent sees before deciding to load the skill."""
    findings = check_skill(_skill(description="Processes PDF files."), today=TODAY)
    assert [f.level for f in findings] == ["warning"]
    assert "when" in findings[0].message


@pytest.mark.parametrize(
    "description",
    [
        "I can help you process PDFs. Use when PDFs appear.",
        "You can use this to process PDFs. Use when PDFs appear.",
        "We handle PDF extraction. Use when PDFs appear.",
    ],
)
def test_first_person_descriptions_are_flagged(description: str) -> None:
    """The guide is explicit: always third person — it goes into the system prompt."""
    findings = check_skill(_skill(description=description), today=TODAY)
    assert any("third person" in f.message for f in findings)


def test_name_must_match_the_directory(tmp_path: Path) -> None:
    directory = tmp_path / "not-the-name"
    directory.mkdir()
    (directory / "SKILL.md").write_text(
        "---\nname: a-skill\ndescription: Does a thing. Use when needed.\n---\n", encoding="utf-8"
    )
    findings = check_skill_directory(directory, today=TODAY)
    assert any(f.is_error and "directory" in f.message for f in findings)


def test_an_overlong_body_is_a_warning(tmp_path: Path) -> None:
    directory = _write(tmp_path, "a-skill", body="filler\n" * 600)
    findings = check_skill_directory(directory, today=TODAY)
    assert any("lines" in f.message and not f.is_error for f in findings)


def test_a_reference_the_agent_cannot_read_is_an_error(tmp_path: Path) -> None:
    """It will try to read it — a dangling pointer is worse than no pointer."""
    directory = _write(tmp_path, "a-skill", body="See [the details](DETAILS.md).\n")
    findings = check_skill_directory(directory, today=TODAY)
    assert any(f.is_error and "DETAILS.md" in f.message for f in findings)


def test_references_deeper_than_one_level_are_flagged(tmp_path: Path) -> None:
    """Nested chains get previewed with `head`, so the agent acts on half a file."""
    directory = _write(tmp_path, "a-skill", body="See [advanced](ADVANCED.md).\n")
    (directory / "ADVANCED.md").write_text("Now see [more](MORE.md).\n", encoding="utf-8")
    (directory / "MORE.md").write_text("The actual information.\n", encoding="utf-8")
    findings = check_skill_directory(directory, today=TODAY)
    assert any("one level deep" in f.message for f in findings)


def test_windows_paths_are_flagged(tmp_path: Path) -> None:
    directory = _write(tmp_path, "a-skill", body="Run [the script](scripts\\\\run.py).\n")
    findings = check_skill_directory(directory, today=TODAY)
    assert any("backslashes" in f.message for f in findings)


# --- Freshness ------------------------------------------------------------------


def test_a_source_without_a_date_is_flagged() -> None:
    body = "## Sources\n\n- [Something](https://example.com/a)\n"
    findings = check_skill(_skill(body=body), today=TODAY)
    assert any("no retrieval date" in f.message for f in findings)


def test_a_stale_source_is_flagged() -> None:
    body = "## Sources\n\n- [Old](https://example.com/a) — retrieved 2025-01-01\n"
    findings = check_skill(_skill(body=body), today=TODAY)
    assert any("last retrieved" in f.message for f in findings)


def test_a_fresh_source_is_silent() -> None:
    body = "## Sources\n\n- [New](https://example.com/a) — retrieved 2026-08-06\n"
    assert check_skill(_skill(body=body), today=TODAY) == []


def test_a_future_date_is_flagged() -> None:
    body = "## Sources\n\n- [Soon](https://example.com/a) — retrieved 2027-01-01\n"
    findings = check_skill(_skill(body=body), today=TODAY)
    assert any("future" in f.message for f in findings)


# --- Withdrawal (W-H) -----------------------------------------------------------


def test_a_withdrawn_skill_says_so_and_names_its_successor() -> None:
    skill = parse_skill(
        "---\nname: a-skill\ndescription: Does a thing. Use when needed.\n"
        "metadata:\n"
        '  speccify.deprecated: "the API it describes was removed"\n'
        '  speccify.superseded-by: "@me/the-new-way"\n'
        "---\n"
    )
    findings = check_skill(skill, today=TODAY)
    assert any("withdrawn" in f.message and "@me/the-new-way" in f.message for f in findings)


# --- Ordering -------------------------------------------------------------------


def test_specification_errors_shadow_style_notes() -> None:
    """Style advice on a broken skill is noise; fix the break first."""
    broken = parse_skill("---\nname: Not-Valid\ndescription: No trigger here.\n---\n")
    findings = check_skill(broken, today=TODAY)
    assert findings and all(f.is_error for f in findings)
    assert not any("third person" in f.message or "when" in f.message for f in findings)


def test_the_shipped_skills_are_clean() -> None:
    """The ten in `skills/` are the product — they may not regress."""
    root = Path(__file__).resolve().parents[2] / "skills"
    directories = find_skills(root)
    assert len(directories) >= 10
    for directory in directories:
        findings = check_skill_directory(directory, today=TODAY)
        assert findings == [], f"{directory.name}: {[f.format() for f in findings]}"


@pytest.mark.links
def test_the_shipped_skills_sources_still_resolve() -> None:
    """Opt-in, needs the network: `pytest -m links`.

    The offline checks cannot tell a live URL from a dead one, and a skill
    whose sources have moved is exactly the failure this project exists to
    catch.
    """
    root = Path(__file__).resolve().parents[2] / "skills"
    for directory in find_skills(root):
        findings = check_skill_directory(directory, links=True, today=TODAY)
        errors = [f.format() for f in findings if f.is_error]
        assert errors == [], f"{directory.name}: {errors}"
