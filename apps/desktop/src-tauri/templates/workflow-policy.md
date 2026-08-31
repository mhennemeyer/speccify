## Board workflow

You are the product owner _and_ the implementer — there is no second agent.
The Speccify app never drives you; it only watches files. Everything below is
plain files inside this project.

### Where everything lives

- Tickets: `.agent/board/<id>.md` — flat `key: value` front matter between
  `---` lines, then a Markdown body. Stations: `Backlog`, `Doing`, `Done`.
- Plans: `.agent/plans/<name>.md`; the active plan has `lifecycle: active`.
- Ticket history: `.agent/board/history/<ticket-id>/index.jsonl` (append-only).
- Skills: `.agent/skills/<name>/SKILL.md` · Tools: `.agent/tools/<name>/TOOL.md`.
- Project actions: `.agent/actions.json` · Project settings: `.agent/settings.json`.

### Getting started

Read the active plan. Slice the next piece of work into small tickets — each
one finishable in a single run. Put them all in `Backlog` with an `order:`
number and `plan: <plan-file-stem>` in the front matter, then log one
`ticket_created` history line per ticket.

### Working a ticket

1. Take the topmost `Backlog` ticket (smallest `order`; ties: oldest
   `created`, then id).
2. Set `station: Doing`. **Only one ticket is ever in `Doing`** — if another
   one is there, finish or park that first.
3. Do the work. Append progress notes to the ticket body as you go; never
   rewrite front matter you do not own.
4. Too big after all? Split it into new `Backlog` tickets and say so in the
   body — do not leave it half-done.
5. When done, set `station: Done` and write an `agent_run` history line.
6. A ticket with `needs_human: true` never moves to `Done` on its own —
   finish your part, set `ready: true`, and leave it in `Doing` for the human.

### Asking the human

Prefer asking in the chat and waiting. If a run has to end without an answer,
append to the ticket body:

```
## Questions

### Q1 · open · 2026-08-31T10:00:00Z
The question, one paragraph.
```

and set `open_question: Q1` in the front matter (always the oldest open
question). When the human answers (`### A1 · bo · <ts>`), copy the outcome
into the ticket and clear or advance `open_question`. Question numbers are
never reused. `needs_human` stays untouched by answers — it marks human
acceptance, not an open question.

### Ticket history — you write it

The app only logs what it changes itself. Append one JSON line per event to
`.agent/board/history/<ticket-id>/index.jsonl`:

```json
{"timestamp":"2026-08-31T10:00:00Z","ticket_id":"my-ticket","event_type":"agent_run","actor":"agent:claude","summary":"Implemented X; skills: speccify","tokens_in":1200,"tokens_out":300,"tokens_cache_read":8000,"tokens_cache_write":0,"duration_ms":45000}
```

`event_type` ∈ `ticket_created | ticket_edited | station_changed | agent_run`;
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
- Mention the ticket id in commit message bodies when you commit.
- Do not commit or push unless the human asks for it.
