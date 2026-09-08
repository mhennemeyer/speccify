---
title: Overview
description: A desktop app that renders the files your agent works with — files, plans, board, actions — one window per project, laid out like Xcode.
sidebar:
  order: 1
---

**The Speccify app** is a desktop app (macOS, Windows and Linux) for running
a project *with* a terminal agent. The agent (Claude Code, Codex, or
any other) does its work in the repository; the app renders that same
repository for you, the owner: the files and the Git state, the plans,
the kanban board, the skills and tools, the project actions. Nothing
lives only in the app — every ticket, plan, and setting is a plain
file under `.agent/`, committed with your code.

![A project window: navigator with icon tabs on the left, board with the active plan above it, the selected ticket in the inspector on the right, agent terminal at the bottom](../../../assets/app/overview.png)

## The division of labor

- **You** decide what gets built, answer the agent's questions, review
  the results, and commit — from the app.
- **The agent** slices plans into tickets, works them one at a time,
  and writes down what it did — from the terminal.
- **The repository** is the single shared state. The app picks up
  file changes on its own: when the agent moves a ticket, your board
  moves; when you answer a question in a ticket, the agent's next run
  sees it.

The contract between the two sides is `.agent/agent.md` — read by
every agent; files like `CLAUDE.md` and `AGENTS.md` just point to it,
so any agent product lands in the same workflow. The first time you
open a project, a workflow banner offers **Set up**: it writes the
versioned workflow block into `.agent/agent.md`, creates the
`/ticket-next` and `/ticket-ask` skills and the `.agent/board` and
`.agent/plans` folders, and links `.claude/skills` and
`.agents/skills` to `.agent/skills` (a junction on Windows) — so
both hosts see the same skills.

## The window

A project window follows the pattern of Xcode: a **navigator** on the
left, the **content** in the middle, an **inspector** on the right,
the **agent terminal** at the bottom, a **toolbar** on top.

- **Navigator.** An icon bar with five areas — **Files** (files, Git),
  **Orga** (playbooks, plans, skills), **Tech** (tools, actions, MCPs,
  agent), **Board**, and **Help** — and, for areas with several tabs,
  a second row naming them. Below that, the list of the active tab.
  An empty list never stays blank: it says what is missing and offers
  the next step — *+ Plan*, *+ Ticket*, *Browse sources*, `git init`,
  or a prompt for the agent.
- **Content.** The selected item at full width: the board, a plan as a
  document, a file in the editor, a diff.
- **Inspector.** Details and actions for whatever is selected on the
  left — a ticket with its *Overview* and *History* tabs, a plan with
  lifecycle, status, *Activate* and *Archive*, a skill with its origin,
  a tool with its per-platform status, the commit panel in the Git tab.
  Hide the inspector and the same panel appears above the content.
- **Terminal.** The agent terminal sits under the content, resizable;
  one click moves it into the right sidebar instead. A session that
  was running when the app quit is **resumed on the next start**
  (`claude --continue`, `codex resume --last`) — the agent reads its
  own transcript and carries on.
- **Toolbar.** The project name on the left; in the middle, buttons
  for actions you pinned there and the **activity view** — what is
  running right now (an action, `git push`, a save, the agent terminal
  while output flows) with its duration, and finished agent runs from
  the ticket history with ticket and tokens; on the right, toggles for
  the three areas, light/dark, and settings. On macOS the toolbar is
  the title bar.

All areas resize by dragging; sizes, visibility, and the terminal
position are remembered per project across restarts. Keyboard: ⌘1–⌘5
switch areas, ⌘0 / ⌥⌘0 / ⇧⌘Y toggle navigator, inspector, and
terminal (Ctrl on Windows).

## Where to go next

- **[Files & Git](/app/files-and-git/)** — the project tree, a code
  editor, and Git with staging, diffs, commits by you or by the agent.
- **[The board](/app/board/)** — tickets in `Backlog`, `In Progress`,
  `Done`; per-ticket history; badges for tickets that wait on you.
- **[Plans & playbooks](/app/plans/)** — one active plan at a time,
  escalations, standing procedures, editors that save as you type.
- **[Questions](/app/questions/)** — how the agent asks and how your
  answer reaches its next run.
- **[Actions](/app/actions/)** — project commands the app runs itself,
  with live output, pinnable to the toolbar.
- **[Skills & tools](/app/skills-tab/)** — what the agent can do here,
  including skills expanded from [Speccify sources](/speccify/overview/).

Start with [the board](/app/board/) — it is where a normal day
happens.
