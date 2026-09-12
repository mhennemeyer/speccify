"""Team board as a static web page: progress read straight from `.agent/specs`.

Spec 031 (Team-Board im Web). Die Quelle ist das Spec-Register — der Ordner
`.agent/specs` bzw. der Inhalt des Branch `specs` (Spec 028). Es gibt keinen
Dienst und keine Datenbank: `render_board` erzeugt eine in sich geschlossene
HTML-Seite (Inline-CSS/-JS, keine externen Abrufe), die z. B. GitHub Actions bei
jedem Push auf `specs` neu baut. Gelesen wird dasselbe flache Front Matter und
dieselbe Task-Liste wie in der Desktop-App: `station`, `order`, `ready`,
`needs_human`, `open_question`, `owner`, `branch`, `parent`, `created` sowie
Markdown-Checkboxen außerhalb von Code-Blöcken; `history.jsonl` liefert die
Aktivität (agent_run, station_changed, …).
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jinja2 import Environment

STATIONS = ("Backlog", "Doing", "Done")
_TASK_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[( |x|X)\]\s+(.*?)\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_HEADING_RE = re.compile(r"^#\s+(.+?)\s*$")
_NUMBER_RE = re.compile(r"^(\d{1,4})-")


@dataclass(frozen=True)
class Task:
    text: str
    done: bool


@dataclass(frozen=True)
class HistoryEvent:
    timestamp: str
    event_type: str
    actor: str
    summary: str
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0

    @property
    def when(self) -> datetime | None:
        return _parse_timestamp(self.timestamp)


@dataclass
class BoardSpec:
    id: str
    file: str
    title: str
    station: str
    number: int | None = None
    order: int | None = None
    ready: bool = False
    needs_human: bool = False
    open_question: str | None = None
    owner: str | None = None
    branch: str | None = None
    parent: str | None = None
    created: str | None = None
    archived: bool = False
    tasks: list[Task] = field(default_factory=list)
    history: list[HistoryEvent] = field(default_factory=list)

    @property
    def tasks_done(self) -> int:
        return sum(1 for task in self.tasks if task.done)

    @property
    def tasks_total(self) -> int:
        return len(self.tasks)

    @property
    def progress(self) -> float:
        """0..1 — Done zählt voll, sonst der Task-Anteil (ohne Tasks 0)."""
        if self.station == "Done":
            return 1.0
        if not self.tasks:
            return 0.0
        return self.tasks_done / self.tasks_total

    @property
    def last_activity(self) -> datetime | None:
        stamps = [event.when for event in self.history if event.when is not None]
        return max(stamps) if stamps else None

    @property
    def owner_name(self) -> str | None:
        if not self.owner:
            return None
        return re.sub(r"\s*<[^>]*>\s*$", "", self.owner).strip() or self.owner

    @property
    def owner_email(self) -> str | None:
        if not self.owner:
            return None
        match = re.search(r"<([^>]+)>\s*$", self.owner)
        return (match.group(1) if match else self.owner).strip().lower()

    @property
    def initials(self) -> str:
        name = self.owner_name or ""
        parts = [part for part in name.split() if part]
        return "".join(part[0].upper() for part in parts[:2]) or "?"

    def to_dict(self) -> dict[str, object]:
        last = self.last_activity
        return {
            "id": self.id,
            "file": self.file,
            "title": self.title,
            "station": self.station,
            "number": self.number,
            "order": self.order,
            "ready": self.ready,
            "needs_human": self.needs_human,
            "open_question": self.open_question,
            "owner": self.owner,
            "branch": self.branch,
            "parent": self.parent,
            "created": self.created,
            "archived": self.archived,
            "tasks_done": self.tasks_done,
            "tasks_total": self.tasks_total,
            "progress": round(self.progress, 4),
            "last_activity": last.isoformat() if last else None,
        }


# --- Parsing -----------------------------------------------------------------


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Flat `key: value` lines between the first two `---` lines; body after."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text
    fields: dict[str, str] = {}
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body = "".join(lines[index + 1 :])
            return fields, body
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip().lower()] = value.strip()
    return {}, text


def parse_tasks(body: str) -> list[Task]:
    """Markdown checkboxes anywhere in the body, ignoring fenced code blocks."""
    tasks: list[Task] = []
    fence: str | None = None
    for line in body.splitlines():
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is not None:
            continue
        match = _TASK_RE.match(line)
        if match:
            tasks.append(Task(text=match.group(2), done=match.group(1).lower() == "x"))
    return tasks


def first_heading(body: str) -> str | None:
    for line in body.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            return match.group(1)
    return None


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"true", "yes", "1"}


def _optional(value: str | None) -> str | None:
    value = (value or "").strip()
    return value if value and value != "null" else None


def _parse_timestamp(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def load_history(path: Path) -> list[HistoryEvent]:
    events: list[HistoryEvent] = []
    if not path.is_file():
        return events
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(raw, dict):
            continue
        events.append(
            HistoryEvent(
                timestamp=str(raw.get("timestamp", "")),
                event_type=str(raw.get("event_type", "")),
                actor=str(raw.get("actor", "")),
                summary=str(raw.get("summary", "")),
                tokens_in=int(raw.get("tokens_in") or 0),
                tokens_out=int(raw.get("tokens_out") or 0),
                duration_ms=int(raw.get("duration_ms") or 0),
            )
        )
    events.sort(key=lambda event: event.timestamp)
    return events


def load_spec(spec_file: Path, *, root: Path, archived: bool = False) -> BoardSpec | None:
    text = spec_file.read_text(encoding="utf-8", errors="replace")
    fields, body = parse_front_matter(text)
    spec_id = spec_file.parent.name
    number_match = _NUMBER_RE.match(spec_id)
    station = fields.get("station") or ("Done" if archived else "Backlog")
    order_raw = fields.get("order", "")
    try:
        order: int | None = int(order_raw) if order_raw.strip() else None
    except ValueError:
        order = None
    return BoardSpec(
        id=spec_id,
        file=spec_file.relative_to(root).as_posix(),
        title=first_heading(body) or _optional(fields.get("title")) or spec_id,
        station=station,
        # Archivordner heißen nach Datum (`2026-09-01-…`); das ist keine laufende Nummer.
        number=int(number_match.group(1)) if number_match and not archived else None,
        order=order,
        ready=_truthy(fields.get("ready")),
        needs_human=_truthy(fields.get("needs_human")),
        open_question=_optional(fields.get("open_question")),
        owner=_optional(fields.get("owner")),
        branch=_optional(fields.get("branch")),
        parent=_optional(fields.get("parent")),
        created=_optional(fields.get("created")),
        archived=archived,
        tasks=parse_tasks(body),
        history=load_history(spec_file.parent / "history.jsonl"),
    )


def load_specs(specs_dir: Path, *, include_archive: bool = True) -> list[BoardSpec]:
    """Every `<slug>/SPEC.md` under `specs_dir` (plus `archive/` when asked)."""
    specs: list[BoardSpec] = []
    roots = [(specs_dir, False)]
    if include_archive:
        roots.append((specs_dir / "archive", True))
    for base, archived in roots:
        if not base.is_dir():
            continue
        for spec_file in sorted(base.glob("*/SPEC.md")):
            spec = load_spec(spec_file, root=specs_dir, archived=archived)
            if spec is not None:
                specs.append(spec)
    return specs


# --- Summary ------------------------------------------------------------------


def summarize(
    specs: list[BoardSpec], *, now: datetime | None = None, days: int = 30
) -> dict[str, object]:
    now = now or datetime.now(UTC)
    live = [spec for spec in specs if not spec.archived]
    stations = Counter(spec.station for spec in live)
    tasks_total = sum(spec.tasks_total for spec in live)
    tasks_done = sum(spec.tasks_done for spec in live)
    people: dict[str, list[BoardSpec]] = defaultdict(list)
    for spec in live:
        if spec.station == "Doing":
            people[spec.owner_name or "ohne Besitzer"].append(spec)
    since = now - timedelta(days=days - 1)
    day_keys = [(since + timedelta(days=offset)).date().isoformat() for offset in range(days)]
    runs: Counter[str] = Counter()
    moves: Counter[str] = Counter()
    tokens: Counter[str] = Counter()
    for spec in live:
        for event in spec.history:
            when = event.when
            if when is None or when < since:
                continue
            key = when.date().isoformat()
            if event.event_type == "agent_run":
                runs[key] += 1
                tokens[key] += event.tokens_in + event.tokens_out
            elif event.event_type == "station_changed":
                moves[key] += 1
    activity = [
        {
            "day": key,
            "runs": runs.get(key, 0),
            "moves": moves.get(key, 0),
            "tokens": tokens.get(key, 0),
        }
        for key in day_keys
    ]
    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "specs": len(live),
        "archived": len(specs) - len(live),
        "stations": {name: stations.get(name, 0) for name in STATIONS},
        "other_stations": {name: count for name, count in stations.items() if name not in STATIONS},
        "tasks_done": tasks_done,
        "tasks_total": tasks_total,
        "progress": (tasks_done / tasks_total) if tasks_total else 0.0,
        "ready": sum(1 for spec in live if spec.ready and spec.station != "Done"),
        "questions": sum(1 for spec in live if spec.open_question and spec.station != "Done"),
        "people": {name: [spec.id for spec in group] for name, group in sorted(people.items())},
        "activity": activity,
        "runs_in_window": sum(runs.values()),
    }


# --- Rendering ------------------------------------------------------------------

_TEMPLATE = r"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} · Team-Board</title>
<style>
:root{--bg:#f8fafc;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--ok:#16a34a;--doing:#2563eb;--warn:#d97706;--ask:#ea580c;--bar:#e2e8f0}
@media(prefers-color-scheme:dark){:root{--bg:#0f172a;--card:#1e293b;--ink:#e2e8f0;--muted:#94a3b8;--line:#334155;--bar:#334155}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1400px;margin:0 auto;padding:20px 16px 48px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:24px 0 8px}
.meta{color:var(--muted);font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:16px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.kpi b{display:block;font-size:22px}.kpi span{color:var(--muted);font-size:12px}
.bar{height:8px;background:var(--bar);border-radius:99px;overflow:hidden}.bar i{display:block;height:100%;background:var(--doing)}
.bar i.done{background:var(--ok)}
.filters{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:12px 0}
.filters input,.filters select{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink)}
.chip{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;padding:4px 10px;font-size:12px;cursor:pointer}
.chip[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.lanes{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.lane{background:color-mix(in srgb,var(--card) 60%,var(--bg));border:1px solid var(--line);border-radius:12px;padding:10px;min-height:120px}
.lane h3{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;margin-bottom:8px}
.card[hidden]{display:none}
.card .t{font-weight:600}.card .n{font-family:ui-monospace,Menlo,monospace;color:var(--muted);font-size:11px;margin-right:6px}
.card .row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:6px;font-size:11px;color:var(--muted)}
.card .bar{margin-top:8px}
.badge{border-radius:99px;padding:1px 7px;font-size:10px;font-weight:600}
.badge.ready{background:#dcfce7;color:#166534}.badge.human{background:#fef3c7;color:#92400e}.badge.ask{background:#ffedd5;color:#9a3412}.badge.idea{background:var(--bar);color:var(--muted)}
.av{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;background:#e0f2fe;color:#075985;font-size:10px;font-weight:700}
.branch{font-family:ui-monospace,Menlo,monospace}
.people{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}
.person{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px}.person b{display:block;margin-bottom:4px}
.person ul{margin:0;padding-left:16px;font-size:12px}
svg.activity{width:100%;height:120px;background:var(--card);border:1px solid var(--line);border-radius:10px}
.legend{font-size:11px;color:var(--muted);margin-top:4px}
footer{margin-top:32px;color:var(--muted);font-size:11px}
</style>
</head>
<body>
<main>
<h1>{{ title }} · Team-Board</h1>
<p class="meta">Stand {{ summary.generated_at }} · Quelle: {{ source }} · {{ summary.specs }} Specs{% if summary.archived %} (+{{ summary.archived }} Altbestand){% endif %}</p>

<div class="kpis">
  <div class="kpi"><b>{{ summary.tasks_done }}/{{ summary.tasks_total }}</b><span>Tasks erledigt</span>
    <div class="bar" style="margin-top:6px"><i class="done" style="width:{{ (summary.progress*100)|round(1) }}%"></i></div></div>
  <div class="kpi"><b>{{ summary.stations.Backlog }}</b><span>Backlog</span></div>
  <div class="kpi"><b>{{ summary.stations.Doing }}</b><span>Doing</span></div>
  <div class="kpi"><b>{{ summary.stations.Done }}</b><span>Done</span></div>
  <div class="kpi"><b>{{ summary.ready }}</b><span>bereit zur Abnahme</span></div>
  <div class="kpi"><b>{{ summary.questions }}</b><span>offene Fragen</span></div>
  <div class="kpi"><b>{{ summary.runs_in_window }}</b><span>Agent-Läufe · 30 Tage</span></div>
</div>

<h2>Aktivität der letzten 30 Tage</h2>
{% set maxv = activity_max %}
<svg class="activity" viewBox="0 0 {{ summary.activity|length * 12 }} 60" preserveAspectRatio="none" role="img" aria-label="Agent-Läufe und Stationswechsel je Tag">
{% for day in summary.activity %}
  {% set h = (day.runs / maxv * 50) if maxv else 0 %}
  {% set m = (day.moves / maxv * 50) if maxv else 0 %}
  <rect x="{{ loop.index0 * 12 + 1 }}" y="{{ 58 - h }}" width="6" height="{{ h }}" fill="#2563eb"><title>{{ day.day }}: {{ day.runs }} Läufe</title></rect>
  <rect x="{{ loop.index0 * 12 + 7 }}" y="{{ 58 - m }}" width="3" height="{{ m }}" fill="#16a34a"><title>{{ day.day }}: {{ day.moves }} Stationswechsel</title></rect>
{% endfor %}
</svg>
<p class="legend">blau: Agent-Läufe · grün: Stationswechsel · {{ summary.activity[0].day }} bis {{ summary.activity[-1].day }}</p>

<h2>Doing nach Person</h2>
<div class="people">
{% for name, ids in summary.people.items() %}
  <div class="person"><b>{{ name }}</b><ul>{% for spec in specs if spec.id in ids %}<li>{% if spec.number is not none %}#{{ spec.number }} {% endif %}{{ spec.title }}{% if spec.branch %} <span class="branch">⎇ {{ spec.branch }}</span>{% endif %} · {{ spec.tasks_done }}/{{ spec.tasks_total }}</li>{% endfor %}</ul></div>
{% else %}
  <p class="meta">Nichts in Doing.</p>
{% endfor %}
</div>

<h2>Board</h2>
<div class="filters">
  <input id="q" type="search" placeholder="Suche · Titel, Nummer, Person, Branch" aria-label="Suche">
  <select id="person" aria-label="Person"><option value="">Alle Personen</option>{% for name in people_names %}<option>{{ name }}</option>{% endfor %}</select>
  <button class="chip" data-flag="ready" aria-pressed="false">bereit</button>
  <button class="chip" data-flag="ask" aria-pressed="false">Frage offen</button>
  <button class="chip" data-flag="human" aria-pressed="false">braucht Abnahme</button>
  <span class="meta" id="count"></span>
</div>
<div class="lanes">
{% for station in lanes %}
  <section class="lane" data-station="{{ station }}"><h3>{{ station }} <span data-lane-count></span></h3>
  {% for spec in specs if spec.station == station and not spec.archived %}
    <article class="card" data-search="{{ spec.search }}" data-person="{{ spec.owner_name or '' }}" data-flags="{{ spec.flags }}">
      <div><span class="n">{% if spec.number is not none %}#{{ spec.number }}{% else %}{{ spec.id }}{% endif %}</span><span class="t">{{ spec.title }}</span></div>
      <div class="row">
        {% if spec.owner %}<span class="av" title="{{ spec.owner }}">{{ spec.initials }}</span>{% endif %}
        {% if spec.branch %}<span class="branch">⎇ {{ spec.branch }}</span>{% endif %}
        {% if spec.parent %}<span>· {{ spec.parent }}</span>{% endif %}
        {% if spec.ready %}<span class="badge ready">bereit</span>{% endif %}
        {% if spec.needs_human %}<span class="badge human">braucht Abnahme</span>{% endif %}
        {% if spec.open_question %}<span class="badge ask">Frage {{ spec.open_question }}</span>{% endif %}
        {% if spec.station == 'Backlog' and spec.order is none %}<span class="badge idea">Idee</span>{% endif %}
        {% if spec.archived %}<span class="badge idea">Altbestand</span>{% endif %}
        {% if spec.age is not none %}<span title="letzte Aktivität {{ spec.last }}">· {% if spec.age == 0 %}heute{% elif spec.age == 1 %}gestern{% else %}vor {{ spec.age }} Tagen{% endif %}</span>{% endif %}
      </div>
      {% if spec.tasks_total %}<div class="bar" title="{{ spec.tasks_done }}/{{ spec.tasks_total }} Tasks"><i class="{% if spec.station == 'Done' %}done{% endif %}" style="width:{{ (spec.progress*100)|round(1) }}%"></i></div>
      <div class="row">{{ spec.tasks_done }}/{{ spec.tasks_total }} Tasks</div>{% endif %}
    </article>
  {% endfor %}
  </section>
{% endfor %}
</div>
{% if archived %}
<details class="archive"><summary class="meta">Altbestand · {{ archived|length }} Specs (nur lesen)</summary>
<ul class="meta">{% for spec in archived %}<li>{{ spec.title }} <span class="n">{{ spec.id }}</span> · {{ spec.station }}{% if spec.tasks_total %} · {{ spec.tasks_done }}/{{ spec.tasks_total }}{% endif %}</li>{% endfor %}</ul>
</details>
{% endif %}
<footer>Erzeugt von <code>speccify board</code> aus dem Spec-Register (Spec 031). Diese Seite ist eine Momentaufnahme; die Wahrheit sind die Dateien im Branch <code>specs</code>.</footer>
</main>
<script>
(function(){
  var q=document.getElementById('q'),person=document.getElementById('person'),count=document.getElementById('count');
  var flags={};
  document.querySelectorAll('.chip').forEach(function(chip){chip.addEventListener('click',function(){var on=chip.getAttribute('aria-pressed')!=='true';chip.setAttribute('aria-pressed',on?'true':'false');flags[chip.dataset.flag]=on;apply();});});
  function apply(){
    var text=(q.value||'').toLowerCase(),who=person.value,shown=0;
    document.querySelectorAll('.card').forEach(function(card){
      var ok=(!text||card.dataset.search.indexOf(text)>=0)&&(!who||card.dataset.person===who);
      for(var f in flags){if(flags[f]&&card.dataset.flags.split(' ').indexOf(f)<0)ok=false;}
      card.hidden=!ok;if(ok)shown++;
    });
    document.querySelectorAll('.lane').forEach(function(lane){lane.querySelector('[data-lane-count]').textContent='('+lane.querySelectorAll('.card:not([hidden])').length+')';});
    count.textContent=shown+' sichtbar';
  }
  q.addEventListener('input',apply);person.addEventListener('change',apply);apply();
})();
</script>
</body>
</html>
"""


def render_board(
    specs: list[BoardSpec],
    *,
    title: str,
    source: str = ".agent/specs",
    now: datetime | None = None,
) -> str:
    """Self-contained HTML page; no external requests, works from file://."""
    now = now or datetime.now(UTC)
    summary = summarize(specs, now=now)
    activity = summary["activity"]
    assert isinstance(activity, list)
    activity_max = max([max(day["runs"], day["moves"]) for day in activity] + [0])
    ordered = sorted(
        specs,
        key=lambda spec: (
            spec.archived,
            spec.order if spec.order is not None else 10**9,
            spec.number if spec.number is not None else 10**9,
            spec.id,
        ),
    )
    rows = []
    for spec in ordered:
        last = spec.last_activity
        flags = " ".join(
            flag
            for flag, present in (
                ("ready", spec.ready),
                ("ask", bool(spec.open_question)),
                ("human", spec.needs_human),
            )
            if present
        )
        rows.append(
            {
                "id": spec.id,
                "number": spec.number,
                "title": spec.title,
                "station": spec.station,
                "order": spec.order,
                "ready": spec.ready,
                "needs_human": spec.needs_human,
                "open_question": spec.open_question,
                "owner": spec.owner,
                "owner_name": spec.owner_name,
                "initials": spec.initials,
                "branch": spec.branch,
                "parent": spec.parent,
                "archived": spec.archived,
                "tasks_done": spec.tasks_done,
                "tasks_total": spec.tasks_total,
                "progress": spec.progress,
                "age": (now - last).days if last else None,
                "last": last.isoformat(timespec="minutes") if last else "",
                "flags": flags,
                "search": " ".join(
                    filter(
                        None,
                        [
                            str(spec.number or ""),
                            spec.title,
                            spec.id,
                            spec.owner_name or "",
                            spec.branch or "",
                            spec.parent or "",
                        ],
                    )
                ).lower(),
            }
        )
    lanes = list(STATIONS) + sorted(
        station
        for station in {spec.station for spec in specs if not spec.archived}
        if station not in STATIONS
    )
    archived = [row for row in rows if row["archived"]]
    people_names = sorted({spec.owner_name for spec in specs if spec.owner_name})
    environment = Environment(autoescape=True)
    template = environment.from_string(_TEMPLATE)
    return template.render(
        title=title,
        source=source,
        summary=summary,
        activity_max=activity_max,
        specs=rows,
        archived=archived,
        lanes=lanes,
        people_names=people_names,
    )
