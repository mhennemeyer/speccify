## Spec workflow

You are the product owner _and_ the implementer — there is no second agent.
The Speccify app never drives you; it only watches files. Everything below is
plain files inside this project.

### Where everything lives

- Specs: `.agent/specs/<slug>/SPEC.md` — flat `key: value` front matter
  between `---` lines, then a Markdown body whose first `#` heading is the
  title. Stations: `Backlog`, `Doing`, `Done`. Finished specs are archived
  under `.agent/specs/archive/<YYYY-MM-DD>-<slug>/`.
- Spec history: `.agent/specs/<slug>/history.jsonl` (append-only).
- Playbooks: `.agent/playbooks/<name>.md` — standing procedures, reused,
  never "worked off".
- Skills: `.agent/skills/<name>/SKILL.md` · Tools: `.agent/tools/<name>/TOOL.md`.
- Project actions: `.agent/actions.json` · Project settings: `.agent/settings.json`.

### What a spec is

One piece of work a human wants to accept in one review: a feature, a
refactor, an investigation. Its body has these sections: `## Why`,
`## What` (scope, and what is out), `## Acceptance` (testable "when …,
then …" statements), `## Decisions` (numbered, dated), `## Tasks`
(checkboxes — the steps, not separate files), `## Verification` (what was
run, what was seen), `## Questions`. Too big for one review → child specs
with `parent: <slug>`; too small → a task in an existing spec. A spec
without `order` is an idea and sorts last.

### Getting started

Read the specs in `Backlog`, smallest `order` first. If the human named a
spec, take that one. Never invent tickets or sub-files: the tasks live in
the spec.

### Working a spec

1. **Backlog → Doing is the human's gate.** Start a spec only when the
   human moved it to `Doing` or asked you to start it. Then set
   `station: Doing` and log `station_changed`. Keep **one spec in `Doing`
   per session**; finish or park it before taking the next.
2. **Attack the spec before building:** missing or untestable acceptance,
   contradictions, hidden dependencies, scope that has silently grown. Fix
   what you can in the spec itself and say so in `## Decisions`; ask the
   rest (below).
3. Work through `## Tasks`: tick `- [x]` as you go, add tasks you discover
   (mark them `(added)`), keep short notes indented under a task. Never
   rewrite front matter you do not own.
4. Record decisions in `## Decisions` and what you verified in
   `## Verification` — commands, results, screenshots, click-throughs.
5. **Done means:** every task ticked, `## Verification` written, an
   `agent_run` history line appended. Then set `station: Done`. With
   `needs_human: true` set `ready: true` instead and leave the spec in
   `Doing` — the human accepts, moves it to `Done` and archives it.
6. Too big after all? Split into child specs (`parent:`), leave the parent
   in `Doing` with the remaining tasks, and say so in the body.

### Asking the human

Prefer asking in the chat and waiting. If a run has to end without an answer,
append to the spec body:

```
## Questions

### Q1 · open · 2026-09-09T10:00:00Z
The question, one paragraph.
```

and set `open_question: Q1` in the front matter (always the oldest open
question). When the human answers (`### A1 · bo · <ts>`), copy the outcome
into `## Decisions` and clear or advance `open_question`. Question numbers
are never reused. `needs_human` stays untouched by answers — it marks human
acceptance, not an open question.

### Spec history — you write it

The app only logs what it changes itself. Append one JSON line per event to
`.agent/specs/<slug>/history.jsonl`:

```json
{"timestamp":"2026-09-09T10:00:00Z","spec_id":"my-spec","event_type":"agent_run","actor":"agent:claude","summary":"Tasks 3–5: …; skills: speccify","tokens_in":1200,"tokens_out":300,"tokens_cache_read":8000,"tokens_cache_write":0,"duration_ms":45000}
```

`event_type` ∈ `spec_created | spec_edited | station_changed | agent_run`;
token and duration fields belong to `agent_run` lines only. Name the skills
and tools you used in `summary`.

### Project actions

`.agent/actions.json` is a JSON array of named commands the human can run from
the app. You may propose one by appending `{"name": …, "command": …,
"description": …, "source": "agent", "confirmed": false}`. Commands are argv
without a shell — no `&&`, pipes or `$(…)`; put chains into a script.

### Rules

- Never write secrets into `.agent/settings.json`, `.mcp.json`,
  `.codex/config.toml`, or any tracked file.
- Mention the spec slug in commit message bodies when you commit.
- Do not commit or push unless the human asks for it.
