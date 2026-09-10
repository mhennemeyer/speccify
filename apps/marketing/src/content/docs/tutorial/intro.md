---
title: What we're building
description: 4Notice, a tiny two-platform notes app — taken from an empty folder to the App Store with Claude Code, the Speccify app, and the Speccify CLI.
sidebar:
  order: 1
---

:::note[Recorded with the ticket workflow]
This tutorial was recorded when the app sliced plans into tickets.
Since v0.6 the unit of work is the **spec** — one folder, tasks as
checkboxes, Backlog → Doing as your gate ([Specs](/app/specs/)). Read
"plan" as *spec* and "ticket" as *task in a spec*; the method, the
questions and the history are unchanged.
:::

This tutorial builds one real app, end to end: **4Notice**, a small
SwiftUI sticky-notes app — four notes, always at hand — for macOS and
iOS from shared sources. The app is deliberately small; the subject
is the method, and the method scales.

By the end, you will have gone from an empty folder to an App Store
submission, and along the road you will have:

- set up a project that a **terminal agent** can work on
  productively — plan, board, actions, all as files in the repo;
- learned to make steady progress with **plans and tickets**, and to
  keep the history honest with **atomic commits**;
- **imported skills** from a source and taken them through
  expand → execute → evaluate;
- **exported your own skill** — a workflow you learned while
  building — into your own Speccify work repo, where your next
  project will find it;
- localized the app, wired up **fastlane** and App Store Connect
  automation, and run pre-release checks before uploading.

## The three tools

| Tool          | Role in this tutorial                                        |
| ------------- | ------------------------------------------------------------ |
| **Claude Code**  | the agent: implements tickets, writes tools, commits       |
| **Speccify app** | the owner's cockpit: board, plans, skills, actions         |
| **Speccify CLI** | the skill/tool manager: sources, expand, check, export     |

None of them is load-bearing for the *result*: everything ends up as
plain files and ordinary Xcode builds. Every step stays inspectable,
every tool replaceable.

## How to read this

The tutorial is honest about its origin: 4Notice is a real project,
and each chapter was written **after** the corresponding step actually
happened there. Chapters whose step hasn't happened yet are visible as
marked stubs — the arc is real, not projected. If you want the
concepts behind any step, the reference sections
([Fundamentals](/fundamentals/overview/),
[Speccify](/speccify/overview/),
[the Speccify app](/app/overview/)) go deeper; the tutorial links
into them rather than repeating them.

First stop: [what you need installed](/tutorial/prerequisites/).
