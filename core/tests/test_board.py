"""Tests for the static team board: parsing `.agent/specs`, summary and HTML.

Pinned here: the same front matter and task rules as the desktop app, Done
counts as complete, activity comes from history.jsonl, and the page is
self-contained (no external URLs) with progress per spec and per person.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from speccify_core.board import (
    load_specs,
    parse_front_matter,
    parse_tasks,
    render_board,
    summarize,
)

NOW = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)


def _spec(root: Path, slug: str, front: str, body: str, history: list[dict] | None = None) -> None:
    folder = root / slug
    folder.mkdir(parents=True)
    (folder / "SPEC.md").write_text(f"---\n{front}\n---\n{body}", encoding="utf-8")
    if history:
        (folder / "history.jsonl").write_text(
            "".join(json.dumps(event) + "\n" for event in history), encoding="utf-8"
        )


def _fixture(tmp_path: Path) -> Path:
    specs = tmp_path / ".agent" / "specs"
    _spec(
        specs,
        "012-login",
        "station: Doing\norder: 2\nowner: Anna Beispiel <anna@example.invalid>\n"
        "branch: spec/012-login\nneeds_human: true",
        "# Login bauen\n\n## Tasks\n\n- [x] eins\n- [ ] zwei\n* [X] drei\n\n"
        "```md\n- [ ] nicht zählen\n```\n",
        [
            {
                "timestamp": "2026-09-11T09:00:00Z",
                "spec_id": "012-login",
                "event_type": "station_changed",
                "actor": "user",
                "summary": "Backlog -> Doing",
            },
            {
                "timestamp": "2026-09-12T08:30:00Z",
                "spec_id": "012-login",
                "event_type": "agent_run",
                "actor": "project",
                "summary": "Tasks 1-2",
                "tokens_in": 1000,
                "tokens_out": 200,
                "duration_ms": 5000,
            },
        ],
    )
    _spec(specs, "013-idee", "station: Backlog", "# Nur eine Idee\n")
    _spec(
        specs,
        "011-fertig",
        "station: Done\norder: 1\nready: true\nopen_question: null",
        "# Fertig\n\n- [x] alles\n",
        [
            {
                "timestamp": "2026-07-20T10:00:00Z",
                "spec_id": "011-fertig",
                "event_type": "agent_run",
                "actor": "project",
                "summary": "alt",
            }
        ],
    )
    _spec(
        specs,
        "014-frage",
        "station: Doing\norder: 3\nopen_question: Q2",
        "# Mit Frage\n\n- [ ] offen\n",
    )
    _spec(specs / "archive" / "2026-01-old", "", "station: Done", "# Alt\n")
    return specs


def test_front_matter_and_tasks_follow_the_app_rules() -> None:
    fields, body = parse_front_matter("---\nstation: Doing\nOrder: 4\n---\n# T\n\n- [ ] a\n")
    assert fields == {"station": "Doing", "order": "4"}
    assert body.startswith("# T")
    assert parse_front_matter("# no front matter\n") == ({}, "# no front matter\n")
    tasks = parse_tasks("- [x] a\n1. [ ] b\n```\n- [ ] c\n```\n~~~\n- [x] d\n~~~\n- [X] e\n")
    assert [(task.text, task.done) for task in tasks] == [("a", True), ("b", False), ("e", True)]


def test_load_specs_reads_fields_tasks_history_and_archive(tmp_path: Path) -> None:
    specs = load_specs(_fixture(tmp_path))
    by_id = {spec.id: spec for spec in specs}
    assert sorted(by_id) == ["011-fertig", "012-login", "013-idee", "014-frage", "2026-01-old"]
    login = by_id["012-login"]
    assert (login.number, login.title, login.station) == (12, "Login bauen", "Doing")
    assert (login.tasks_done, login.tasks_total) == (2, 3)
    assert login.progress == 2 / 3
    assert login.owner_name == "Anna Beispiel"
    assert login.owner_email == "anna@example.invalid"
    assert login.initials == "AB"
    assert login.branch == "spec/012-login"
    assert login.needs_human and not login.ready
    assert login.last_activity == datetime(2026, 9, 12, 8, 30, tzinfo=UTC)
    assert by_id["011-fertig"].progress == 1.0
    assert by_id["013-idee"].order is None and by_id["013-idee"].tasks == []
    assert by_id["014-frage"].open_question == "Q2"
    old = by_id["2026-01-old"]
    assert old.archived and old.station == "Done" and old.number is None
    assert load_specs(tmp_path / "missing") == []


def test_summary_counts_progress_people_and_activity(tmp_path: Path) -> None:
    summary = summarize(load_specs(_fixture(tmp_path)), now=NOW)
    assert summary["specs"] == 4 and summary["archived"] == 1
    assert summary["stations"] == {"Backlog": 1, "Doing": 2, "Done": 1}
    assert (summary["tasks_done"], summary["tasks_total"]) == (3, 5)
    assert summary["ready"] == 0, "Done zählt nicht als bereit zur Abnahme"
    assert summary["questions"] == 1
    assert summary["people"] == {"Anna Beispiel": ["012-login"], "ohne Besitzer": ["014-frage"]}
    activity = summary["activity"]
    assert len(activity) == 30 and activity[-1]["day"] == "2026-09-12"
    assert activity[-1]["runs"] == 1 and activity[-1]["tokens"] == 1200
    assert activity[-2]["moves"] == 1
    assert summary["runs_in_window"] == 1, "der alte Lauf liegt außerhalb der 30 Tage"


def test_render_is_self_contained_and_shows_progress(tmp_path: Path) -> None:
    page = render_board(
        load_specs(_fixture(tmp_path)), title="Demo", source="specs@abc123", now=NOW
    )
    assert page.startswith("<!doctype html>")
    assert "http://" not in page and "https://" not in page, "keine externen Abrufe"
    assert "Demo · Team-Board" in page
    assert "3/5" in page and "Tasks erledigt" in page
    assert (
        "Login bauen" in page
        and "⎇ spec/012-login" in page
        and 'title="Anna Beispiel &lt;anna@example.invalid&gt;">AB' in page
    )
    assert "Doing nach Person" in page and "Anna Beispiel" in page and "ohne Besitzer" in page
    assert 'class="badge ask">Frage Q2' in page
    assert 'class="badge human">braucht Abnahme' in page
    assert 'class="badge idea">Idee' in page
    assert 'style="width:66.7%"' in page
    assert "heute" in page and "Altbestand · 1 Specs" in page and "<details" in page
    assert (
        'data-station="Backlog"' in page
        and 'data-station="Doing"' in page
        and 'data-station="Done"' in page
    )
    assert "<script" in page and "Quelle: specs@abc123" in page
