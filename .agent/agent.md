# Speccify project guidance

Sprache mit dem Nutzer: Deutsch, Ansprache „Du“. Produkttexte und öffentliche
Dokumentation sind Englisch, sofern der jeweilige Bestand nichts anderes
vorgibt.

## Produkt

Speccify ist ein agentenagnostischer Skill- und Tool-Manager für macOS und
Windows. Wiederverwendbares Wissen wird als `SKILL.md` über Git geteilt.
Plattformabhängige Werkzeuge werden nicht als fertige Skripte vorausgesetzt,
sondern durch `TOOL.md` spezifiziert und im Zielprojekt für die jeweilige
Plattform implementiert und geprüft.

Die Arbeit läuft über Specs unter `.agent/specs/` (Board Backlog / Doing /
Done, Tasks als Checkboxen; die Policy dazu liegt als Vorlage in
`apps/desktop/src-tauri/templates/workflow-policy.md` und kommt per
Einrichten-Knopf in die `agent.md` eines Projekts);
das Skill-und-Tool-Modell steht in `.agent/specs/001-skills-und-tools/SPEC.md`,
das Projektfenster im Archiv unter `.agent/specs/archive/`.
Beide sind auf ausdrücklichen BO-Entscheid parallel aktiv.

## Kanonische Projektstruktur

- `.agent/skills/<name>/SKILL.md`: normale, projektspezifische Skills.
- `.agent/tools/<name>/TOOL.md`: Tool-Vertrag; Implementierungen daneben als
  `<platform>.<ext>`.
- `.agent/speccify/expansions.yaml`: Herkunft, Hashes und Prüfstatus.
- `.agent/specs/<NNN-slug>/SPEC.md`: **eine Arbeitseinheit** (Spec, „Spec 12"
  im Gespräch) mit
  Stationen Backlog / Doing / Done und Tasks als Checkboxen; Fertiges bleibt
  in Done am selben Ort. `.agent/specs/archive/` ist erhaltener Altbestand.
  Ersetzt seit 2026-09-09 Pläne und Tickets
  (Spec `spec-workflow`); die alten Pläne liegen konvertiert im Archiv.
- `.agent/playbooks/`: stehende Anleitungen (Release, Deploy, …) — anders
  als Specs werden sie nicht abgearbeitet, sondern wiederverwendet.
- `.agent/actions.json`: benannte Projektaktionen.

Agent-spezifische Ordner sind nur Adapter: `.claude/skills` und
`.agents/skills` zeigen beide auf `.agent/skills`. Bearbeite Skills immer an
der kanonischen Stelle.

## Architektur

- `core/`: Python-Domänenlogik für Skills, Quellen, Lockfiles, Expansion und
  Tool-Prüfung.
- `cli/`: dünner Typer-Adapter über den Core.
- `mcp/`: dünner MCP-Adapter über denselben Core.
- `crates/`: Rust-MCPs für Exec, Discovery, Parallels und Toolbox.
- `apps/desktop/`: React/Tauri-2-App für macOS und Windows.
- `apps/marketing/`: öffentliche Website und Dokumentation.

CLI, MCP und Desktop dürfen keine parallelen Domänenmodelle erfinden. Neue
Funktionalität gehört zuerst in den Core oder in einen klaren, nativen
Desktop-Vertrag; Adapter bleiben klein.

## Arbeitsregeln

Die lebende Produktvision, Ausbauphasen und Arbeitsweise stehen in
`.agent/playbooks/weiterentwicklung.md`; den aktuellen Implementierungs- und
Prüfstand samt vollständigem funktionalem UI-Baum hält
`.agent/playbooks/stand-und-ui.md` fest. Bei Änderungen an Produktumfang,
Navigation oder dauerhaftem Arbeitsablauf beide Playbooks im selben
Änderungssatz prüfen und die betroffenen Abschnitte aktualisieren. Ziele und
Vorschläge sind keine bereits implementierten Fähigkeiten. Der überprüfte Ausgangspunkt vom
2026-09-10 steht in `.agent/specs/006-bestandsaufnahme-agent-terminal/SPEC.md`,
die vorgeschlagenen Folgeschritte in Specs 007–012. `.agent/status.md` und
`.agent/resume.md` enthalten ältere Produktstände und sind keine aktuelle
Arbeitsanweisung. Spec 008 vereinheitlicht Aufgaben und Workflow-Diagnose;
das eigene Repo verwendet Policy v5 und die versionierten Workflow-Skills.

Nutzerentscheidung 2026-09-10 (Specs 019–022): Farbkonzept und UI-Findings stehen
zusätzlich in `.agent/playbooks/ui-gestaltung.md`. Archivieren entfällt als
gewünschter Workflow-Schritt; abgeschlossene Specs vorerst an Ort und Stelle
in Done belassen. Altbestand unter archive nicht löschen oder pauschal umziehen.
Spec 020 löst die Archiv-UI durch eine durchsuchbare Gesamtliste ab; Policy v5
beschreibt denselben Abschluss ohne Dateiverschiebung.

Für laufende Nutzung und Abnahme die lokale gebündelte App ohne Watcher offen
halten (Spec 013; Startkommandos im Weiterentwicklungs-Playbook). Vor und nach
Änderungen den App-Status prüfen und keine fremden Portbesitzer beenden.
Neustarts für Updates sind ausdrücklich erlaubt und erwünscht (2026-09-10),
aber anschließend die App wieder starten und die Wiederaufnahme prüfen.
Entwürfe und laufende Aufträge beachten; einen Neustart kurz ankündigen, nicht
bei jedem Update erneut um Erlaubnis fragen. Ein aktuelles „jetzt nicht neu
starten“ hat Vorrang. Betrieb/Handshake ist noch keine menschliche Abnahme.

- Bestehende Nutzeränderungen nicht überschreiben oder zurücksetzen.
- Für Textänderungen die Editier-Werkzeuge des jeweiligen Hosts verwenden
  (Codex: `apply_patch`; Claude Code: Edit/Write) — keine sed/awk-Umbauten.
- Python: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`.
- Desktop-Frontend: `pnpm --filter speccify-desktop typecheck`.
- Desktop-Rust: `cargo test -p speccify-desktop` und `cargo fmt --check`.
- Gezielte Tests zuerst, breitere Checks nach erfolgreichem Kernpfad.
- Keine Secrets in `.mcp.json`, `.codex/config.toml`, `.agent/settings.json`
  oder andere getrackte Projektdateien schreiben.
- Committen ist in diesem Repo ausdrücklich erlaubt (BO, 2026-08-31:
  „committe gern selbst in diesem Projekt") — in sich abgeschlossene
  Conventional Commits mit Verifikationsstand. **Pushen** ebenfalls
  erlaubt (BO, 2026-09-06: „Mach commits und push gern selbst") — nach
  grünem Verifikationsstand; ein Push auf `main` deployt die Website
  (pages.yml), Tags lösen den Release-Workflow aus und bleiben BO-Zuruf.

## Skills und Tools

Lies einen passenden Skill vollständig, bevor Du ihn benutzt. `TOOL.md` ist
der Vertrag: Eingaben, Ausgaben, Effekte, Anforderungen und Beispiele müssen
vor einer Implementierung verstanden sein. Prüfe Implementierungen mit
`speccify tool check <name>`; ändere den Status in `expansions.yaml` nie von
Hand. `speccify verify` prüft Lock-, Bundle-, Expansions- und Tool-Drift.

<!-- speccify:workflow:begin v6 -->
## Spec workflow

The human owns priorities, authorization and acceptance; you implement the
requested spec. The Speccify app watches project files, it does not grant
permission or direct your work. Explicit project and host rules take
precedence over these workflow defaults, including commit/push permissions
and attribution/provenance restrictions.

### Where everything lives

- Specs: `.agent/specs/<NNN-slug>/SPEC.md` — the folder name is the id,
  its running number (`012-…`) is how people refer to the spec ("spec 12");
  flat `key: value` front matter between `---` lines, then a Markdown body
  whose first `#` heading is the title. Stations: `Backlog`, `Doing`,
  `Done`. Finished specs stay in place in `Done`; there is no archiving step.
  Existing `.agent/specs/archive/` content is historical, remains discoverable
  and is read-only in spec actions. Do not delete or relocate it automatically.
  New specs take the next free number, including historical numbers
  (the app does this; by hand: highest number + 1).
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
   The board counts Markdown task lists throughout the spec body, excluding
   code blocks. Put illustrative checkboxes in fenced code blocks.
4. Record decisions in `## Decisions` and what you verified in
   `## Verification` — commands, results, screenshots, click-throughs.
5. **Done means:** every task ticked, `## Verification` written, an
   `agent_run` history line appended. Then set `station: Done`. With
   `needs_human: true` set `ready: true` instead and leave the spec in
   `Doing` — the human accepts and moves it to `Done`, without moving files.
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
{"timestamp":"2026-09-09T10:00:00Z","spec_id":"my-spec","event_type":"agent_run","actor":"project","summary":"Tasks 3–5: …; skills: speccify"}
```

`event_type` ∈ `spec_created | spec_edited | station_changed | agent_run`;
token and duration fields belong to `agent_run` lines only. Name the skills
and tools you used in `summary`.
Use an actor label permitted by the project's provenance rules. Include
token/duration measurements only when actually available; do not invent them.

### Project actions

`.agent/actions.json` is a JSON array of named commands the human can run from
the app. You may propose one by appending `{"name": …, "command": …,
"description": …, "source": "agent", "confirmed": false}`. Commands are argv
without a shell — no `&&`, pipes or `$(…)`; put chains into a script.

### Shared spec register (team)

When `.agent/specs` is a Git worktree of the branch `specs` (a `.git` *file*
inside it), the specs are the team's shared register: the same path for
everyone, independent of the code branch. Edit specs there as usual. The
Speccify app commits and syncs the register (commit → fetch → rebase → push,
never force). Do not commit inside `.agent/specs` yourself while the app is
running; without the app, run `git -C .agent/specs add -A && git -C
.agent/specs commit -m "spec(<id>): …" && git -C .agent/specs pull --rebase
&& git -C .agent/specs push`, never `--force`. A stopped rebase with conflict
markers in a `SPEC.md` is a human decision: report it, do not resolve it
silently. In a fresh clone without the worktree, mount it with
`git worktree add .agent/specs origin/specs` (the app offers the same under
"Einrichten"). Never add `.agent/specs` to a code branch commit.

### Rules

- Never write secrets into `.agent/settings.json`, `.mcp.json`,
  `.codex/config.toml`, or any tracked file.
- Mention the spec id (`012-slug`) in commit message bodies when you commit.
- Commit/push only within explicit authorization, including standing project
  permissions. This default does not revoke permissions already granted.
<!-- speccify:workflow:end -->
