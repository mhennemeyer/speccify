---
station: Doing
order: 10
created: 2026-09-09
---
# Plan: Specs statt Pläne und Tickets — eine Arbeitseinheit, drei Stationen

> **BO (2026-09-09):** In einem anderen Projekt heißen Pläne „Specs" und
> durchlaufen Phasen (Backlog → Progress → Done) statt kleinschnittiger
> Tickets. Die Pläne und der Ticket-Zuschnitt in Speccify sind „noch nicht
> ganz rund" und stammen aus der Zeit, als kleine Tickets Tokens sparen
> sollten — obsolet. Solange es keine Nutzer gibt, sind wir frei.

Recherche: `~/Desktop/Work/Agents-Research/2026-09-09 Spec-Workflow statt
Pläne und Tickets.md` (Spec Kit, OpenSpec, Kiro, BMAD, Tessl, O'Reilly
„right amount of spec"). Kurzfassung: Es gibt keinen Standard, aber eine
klare Konvention — ein Ordner je Spec, eine Hauptdatei, Aufgaben als
Checkboxen, Anforderungen testbar, Phasen mit menschlichem Gate, Archiv
statt Löschen. Keines der Werkzeuge hat Board, History oder KPIs.

## Was heute stört

* Drei Ebenen für eine Arbeit: Plan (strategisch, Status als Prosa im
  Frontmatter) → Ticket („in einem Lauf schaffbar") → History. Ein
  aktuelles Modell erledigt das, wofür wir drei Tickets schnitten, in
  einem Rutsch; die Ticket-Ebene ist Verwaltung ohne Nutzen.
* Pläne kennen `draft/active/onHold/done` und „ein aktiver Plan" — aber
  wir arbeiten längst an zwei Plänen parallel (BO-Ausnahme), und der
  Fortschritt steht als Fließtext im `status:`.
* Board und Pläne sind zwei Tabs mit zwei Modellen (`board_cmd.rs`,
  `plan_cmd.rs`), die nur über `plan: <stem>` zusammenhängen.

## Was bleibt, weil es die anderen nicht haben

Board mit Stationen und Live-Watcher, `needs_human`/`ready` als
Abnahme-Gate, Q&A-Protokoll (`open_question`, `### Q1 · open`), History-
JSONL mit `agent_run`-KPIs, Aktivitätsanzeige, Playbooks, das Skill-Modell
(Expand/Execute/Evaluate), Aktionen.

## Zielbild

**Eine Arbeitseinheit: die Spec.** `.agent/specs/<slug>/SPEC.md`:

```markdown
---
station: Backlog          # Backlog | Doing | Done
order: 10                 # Reihenfolge im Backlog
created: 2026-09-09
needs_human: false        # Abnahme durch Menschen nötig
ready: false              # Agent fertig, wartet auf Abnahme
open_question: null       # Q-Nummer der ältesten offenen Frage
parent: null              # optionale Ober-Spec (Thema)
---
# Skills aus beliebigen Git-Repos importieren

## Warum
Eine bis drei Sätze: Anlass, Nutzen, wer es braucht.

## Was (Scope)
Was drin ist, was ausdrücklich nicht.

## Akzeptanz
- Wenn eine Git-URL als Quelle eingetragen wird, dann klont die App sie
  einmal und zeigt ihre Skills im Browser.
- Wenn der Zugang fehlt, dann zeigt die App die git-Meldung und einen
  Anmeldehinweis.

## Entscheidungen
- D1 … (mit Datum und Wer)

## Tasks
- [x] Quellen-Modell in Rust
- [ ] Bibliothek im Dashboard
- [ ] Doku

## Prüfung
Was wurde wie verifiziert (Tests, Screenshots, Klick-Test).

## Fragen
### Q1 · open · 2026-09-09T10:00:00Z
…
```

* **Stationen:** `Backlog → Doing → Done`. Das Gate Backlog → Doing ist
  die menschliche Freigabe (wie Kiros Approval); `Done` verlangt alle
  Tasks abgehakt, einen `## Prüfung`-Eintrag und bei `needs_human` die
  Abnahme (`ready` → Mensch zieht auf Done). Erledigtes wandert nach
  `.agent/specs/archive/YYYY-MM-DD-<slug>/`.
* **Tasks** sind Checkboxen in der Spec — die heutigen „kleinen Tickets"
  ohne eigene Dateien. Der Agent pflegt sie, das Board zeigt `3/7`.
* **Größe:** eine Spec ist, was ein Mensch in einem Review abnehmen
  will — ein Feature, ein Umbau, eine Untersuchung. Zu groß → `parent:`
  mit Unter-Specs; zu klein → ein Task in einer bestehenden Spec.
* **History** je Spec: `.agent/specs/<slug>/history.jsonl` (gleiches
  Format wie heute: `ticket_created` → `spec_created`, `station_changed`,
  `agent_run`, `spec_edited`).
* **Themen/Roadmap:** die heutigen strategischen Pläne werden entweder
  zu Specs mit Unter-Specs (`parent`) oder zu einer kurzen
  `.agent/ROADMAP.md`, die Reihenfolge und Verweise hält. Keine
  Status-Prosa mehr im Frontmatter.
* **Vor dem Bauen:** der Agent greift die Spec an (Lücken, Widersprüche,
  nicht testbare Akzeptanz) — als Schritt im `spec-next`-Skill, nicht als
  eigene Phase.
* **Nicht:** kein `proposal/design/tasks`-Dreiklang als Pflicht, keine
  Personas, keine „Verhaltens-Specs als Quelle der Wahrheit" neben Code
  und Hilfe (O'Reilly: konkurrierende Wahrheiten). `design.md` neben der
  SPEC.md ist erlaubt, wenn es groß wird.

## Entscheidungen (BO, 2026-09-09, per Rückfrage im Chat)

* **D1/D2:** Arbeitseinheit heißt **Spec**, Stationen **Backlog / Doing /
  Done**, keine vierte Station — eine Spec ohne `order` gilt als Idee.
* **D3:** **Eine Spec in Doing je Agent-Sitzung** (Policy); das Board
  erzwingt nichts.
* **D4:** Tasks als Checkboxen **in der SPEC.md** unter `## Tasks`.
* **D5:** **Pläne-Tab entfällt komplett**; `.agent/plans/` bleibt als
  Dateien lesbar (Dateien-Tab), die App zeigt sie nicht mehr an.
* **D6:** iKanbanAI-Format (D19) **aufgegeben**.
* **D7:** **Aktive Pläne → Specs** (ide-im-projektfenster, skill-quellen-
  und-export, skills-und-tools; Meilensteine → Tasks), alle anderen Pläne
  und die Tickets ins Spec-Archiv.
* **D8:** Verhaltens-Specs **jetzt nicht**, später prüfen.
* **Navigator:** Gruppe „Board" wird **„Specs"**; „Orga" behält Playbooks
  und Skills.

### Die Fragen, wie sie gestellt wurden

* **D1 Name.** „Spec" (Vorschlag) — passt zu Speccify und zum Markt; die
  Tabs heißen dann „Specs" statt „Pläne" + „Board".
* **D2 Stationen.** `Backlog / Doing / Done` (Vorschlag, wie heute) oder
  `Backlog / Progress / Done` (BO-Wortlaut). Zusätzlich `Ideen`/`Draft`
  als vierte Station vor Backlog? Vorschlag: nein — eine Spec ohne
  `order` gilt als Idee und steht unten.
* **D3 Ein Doing?** Heute darf nur ein Ticket in Doing sein. Specs sind
  größer und Mensch + Agent arbeiten parallel — Vorschlag: **ein Doing je
  Agent-Sitzung** (Policy), das Board erzwingt nichts.
* **D4 Tasks in der SPEC.md** (Vorschlag, eine Datei, ein Editor) oder
  separat in `tasks.md` (OpenSpec/Kiro)?
* **D5 Pläne-Tab.** Entfällt zugunsten des Specs-Boards; Playbooks
  bleiben ein eigener Tab. Alte Pläne bleiben unter `.agent/plans/` lesbar,
  die App zeigt sie nicht mehr an (oder nur als Archiv-Liste).
* **D6 iKanbanAI-Format (D19).** Aufgeben — iKanbanAI ist zurückgestellt,
  das flache Ticket-Frontmatter bleibt aber fast identisch, ein späterer
  Client hätte es leicht.
* **D7 Migration eigener Bestände.** Speccify-Repo: aktive Pläne werden zu
  Specs (Meilensteine → Tasks, erledigte Meilensteine abgehakt), alte
  Pläne ins Spec-Archiv; AVC: dort liegt ein `migration-status.md` und ein
  Playbook — AVC bleibt unangetastet, bis BO dort umstellt.
* **D8 Verhaltens-Specs später?** OpenSpecs `specs/`-Ordner (aktuelles
  Verhalten als Quelle der Wahrheit, Änderungen als Deltas) als spätere
  Option, wenn mehrere Menschen am selben Verhalten arbeiten. Jetzt nicht.

## Meilensteine

**S1 — Format und Policy (kein Code).** Spec-Vorlage, `workflow-policy.md`
neu (Spec statt Ticket, Gate, Done-Regel, Angriff auf die Spec vor dem
Bauen), Skills `spec-next` und `spec-ask` (ersetzen `ticket-next`/
`ticket-ask`), `agent.md`-Abschnitt. *Fertig heißt:* ein `claude -p`-Lauf
folgt dem Protokoll nachweislich (wie W1 damals).

**S2 — Rust: `spec_cmd.rs` statt `board_cmd.rs` + `plan_cmd.rs`.** Parser für
SPEC.md (Frontmatter + Tasks-Zähler + Fragen), Stationen, History, KPIs,
Archivieren, Anlegen aus Vorlage; Watcher-Bereich `specs`; `project_board_
kpis` bleibt namentlich für die Aktivitätsanzeige. **Rust-Änderung → BOs
Dev-App startet neu**, in einem Commit bündeln.

**S3 — App: Specs-Board.** Board-Tab zeigt Specs als Karten (Titel,
`3/7` Tasks, Badges `?`/`braucht mich`/`bereit`), Inspektor mit Tabs
Übersicht | Tasks | Fragen | Historie, Editor für SPEC.md (Autosave,
Doppelklick), Anlegen aus Vorlage, Archivieren. Pläne-Tab entfällt,
Navigator-Gruppe „Orga" = Playbooks | Specs? (oder Specs in „Board").
Toolbar-Knopf „+ Spec".

**S4 — Migration.** Skript oder Kommando `speccify specs migrate`:
`.agent/board/*.md` → je Ticket eine Spec **oder** Tasks einer Spec
(`plan:`-Bezug), Pläne → Specs/Archiv, History mitnehmen. Eigenes Repo
umstellen, Mock/Fixtures anpassen.

**S5 — Doku.** Hilfe, Website (`app/board`, `app/plans` → `app/specs`),
Templates in `templates/`, Speccify-Skill (Bezug auf Tickets raus).

Aufwand: S1 ein halber Tag, S2 + S3 zwei Tage, S4 + S5 ein Tag — als
Sessions gerechnet. Reihenfolge fest, weil S2/S3 ohne S1-Vorlage ins Blaue
bauen würden.

## Nicht in diesem Plan

Verhaltens-Specs als Quelle der Wahrheit (D8), Personas/Agent-Rollen,
Branch-je-Spec-Automatik (Spec Kit) — der Git-Tab reicht; iKanbanAI-
Kompatibilität.

## Tasks

* [x] S1 Format und Policy: Vorlage, Policy v2, Skills spec-next/spec-ask, E2E mit `claude -p`
* [x] S2 Rust: board_cmd/project_cmd auf `.agent/specs`, Tasks, Archiv, plan_cmd entfernt
* [x] S3 App: Specs-Board mit Fortschritt, Inspektor-Tabs Übersicht/Tasks/Historie, Pläne-Tab raus
* [x] S4 Migration des eigenen Repos (Pläne → Specs/Archiv)
* [x] S5 Doku: Hilfe, Website (app/specs), Templates, Speccify-Skill
* [ ] BO-Prüfung in der echten App

## Stand bei der Migration (2026-09-09)

BO 2026-09-09 „Dein Vorschlag klingt super, lass uns das so machen" — D1–D8 entschieden (s. unten), S1 Format + Policy läuft
