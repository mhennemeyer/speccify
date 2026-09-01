---
title: Überblick
description: Der .agent-Ordner — ein Ort im Repository für Plan, Board, Skills und Tools.
sidebar:
  order: 1
---

Alles, was der Workflow braucht, liegt in einem Ordner im Wurzelverzeichnis
des Repositories:

```text
.agent/
├── agent.md          # der Workflow-Vertrag — wie der Agent hier arbeitet
├── plans/            # was wir bauen wollen (Markdown, eine Datei pro Plan)
├── board/            # das Kanban-Board (eine Markdown-Datei pro Ticket)
│   └── history/      # append-only-Log pro Ticket (JSONL)
├── skills/           # wiederverwendbare Anweisungen für den Agenten
│   └── <name>/SKILL.md
└── tools/            # kleine geprüfte Programme, die Skills aufrufen
    └── <name>/TOOL.md + eine Implementierung pro Plattform
```

Drei Eigenschaften machen das tragfähig:

- **Einfache Dateien.** Pläne, Tickets, Skills und Tool-Verträge sind
  Markdown mit YAML-Frontmatter; die History ist JSONL. Alles ist im
  Diff reviewbar und überlebt jeden Werkzeugwechsel.
- **Agent-agnostisch.** `agent.md` ist die einzige Wahrheit für den
  Workflow. Agent-spezifische Einstiege (`CLAUDE.md`, `AGENTS.md`)
  verweisen nur dorthin, und agent-spezifische Skill-Ordner wie
  `.claude/skills` sind Symlinks nach `.agent/skills/` — ein Skill
  einmal angelegt, jeder Agent sieht ihn.
- **Zwei Leser, ein Zustand.** Der Agent liest und schreibt diese
  Dateien vom Terminal aus; die [Speccify-App](/de/app/overview/)
  rendert dieselben Dateien für den Owner. Es gibt kein
  Synchronisationsproblem, weil es nichts zu synchronisieren gibt.

Der Rest dieser Section behandelt die Bausteine der Reihe nach:
[Skills](/de/fundamentals/skills/) (was der Agent zu tun weiß),
[Tools und Tool-Specs](/de/fundamentals/tools/) (kleine Programme mit
striktem, testbarem Vertrag) und [MCPs](/de/fundamentals/mcps/) (wie
ein Agent über das Dateisystem hinausreicht).
