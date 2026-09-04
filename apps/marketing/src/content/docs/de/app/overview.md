---
title: Überblick
description: Eine Desktop-App, die die Dateien rendert, mit denen dein Agent arbeitet — Board, Pläne, Skills und Aktionen, ein Fenster pro Projekt.
sidebar:
  order: 1
---

**Die Speccify-App** ist eine Desktop-App (macOS und Windows), um ein
Projekt *mit* einem Terminal-Agenten zu führen. Der Agent (Claude
Code, Codex oder ein anderer) arbeitet im Repository; die App rendert
dasselbe Repository für dich, den Owner: das Kanban-Board, die Pläne,
die Skills und Tools, die Projekt-Aktionen. Nichts lebt nur in der
App — jedes Ticket, jeder Plan, jede Einstellung ist eine einfache
Datei unter `.agent/`, committet mit deinem Code.

![Ein Projektfenster: Board mit aktivem Plan darüber, Agent-Terminal rechts](../../../../assets/app/overview.png)

## Die Arbeitsteilung

- **Du** entscheidest, was gebaut wird, beantwortest die Fragen des
  Agenten und prüfst die Ergebnisse — aus der App.
- **Der Agent** schneidet Pläne in Tickets, arbeitet sie einzeln ab
  und schreibt auf, was er getan hat — vom Terminal aus.
- **Das Repository** ist der eine geteilte Zustand. Die App nimmt
  Dateiänderungen von selbst auf: Verschiebt der Agent ein Ticket,
  bewegt sich dein Board; beantwortest du eine Frage im Ticket, sieht
  es der nächste Lauf des Agenten.

Der Vertrag zwischen beiden Seiten ist `.agent/agent.md` — gelesen
von jedem Agenten; Dateien wie `CLAUDE.md` und `AGENTS.md` verweisen
nur dorthin, sodass jedes Agent-Produkt im selben Workflow landet.
Beim ersten Öffnen eines Projekts bietet ein Workflow-Banner
**Einrichten** an: Es schreibt den versionierten Workflow-Block in
`.agent/agent.md`, legt die Skills `/ticket-next` und `/ticket-ask`
sowie die Ordner `.agent/board` und `.agent/plans` an und verlinkt
`.claude/skills` und `.agents/skills` auf `.agent/skills` (auf
Windows als Junction) — beide Hosts sehen dieselben Skills.

## Dashboard und Projektfenster

Die App startet auf einem **Dashboard** — deine Projekte, dazu das
Geteilte: Bibliothek, Umgebung, Server, Agents, Settings. Jedes
Projekt öffnet sich in einem **eigenen Fenster** mit den Tabs
**Board, Playbooks, Pläne, Skills, Tools, Aktionen, MCPs, Agent,
Hilfe** in einem Navigator links, dem Inhalt in der Mitte und einem
**Inspektor** rechts, der das Ausgewählte zeigt (etwa ein Ticket mit
seiner History). Das Agent-Terminal lebt wahlweise als Tab in dieser
rechten Seitenleiste oder in einer höhenverstellbaren Leiste unten —
pro Projekt Deine Wahl. Alle drei Bereiche lassen sich ziehen und
über die Toolbar ausblenden, wie in Xcode. Claude Code und Codex sind
dort gleichberechtigte Presets — nichts im Workflow ist auf einen von
beiden festgelegt.

- **[Das Board](/de/app/board/)** — Tickets in `Backlog`,
  `In Progress`, `Done`; History je Ticket; Badges für Tickets, die
  auf dich warten.
- **[Pläne & Playbooks](/de/app/plans/)** — die Markdown-Pläne
  unter `.agent/plans/`, mit genau einem `active`, einem
  Eskalations-Banner, wenn der Agent dich braucht, und **Als Prompt
  kopieren**; daneben die Playbooks unter `.agent/playbooks/` —
  stehende Anleitungen wie ein Release, die wiederverwendet statt
  abgearbeitet werden.
- **[Skills & Tools](/de/app/skills-tab/)** — was der Agent
  hier kann, einschließlich Skills aus
  [Speccify-Quellen](/de/speccify/overview/).
- **[Aktionen](/de/app/actions/)** — Projekt-Kommandos, die die
  App selbst ausführt, mit Live-Ausgabe.

Fang mit [dem Board](/de/app/board/) an — dort passiert der
normale Tag.
