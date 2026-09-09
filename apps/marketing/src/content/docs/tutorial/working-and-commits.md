---
title: Working & atomic commits
description: "Steady progress you can audit: one meaningful step, one commit."
sidebar:
  order: 5
---

An agent produces a lot of change fast. Commit discipline keeps that
change auditable — four rules from the workflow contract
(`agent.md`):

1. **One commit per meaningful step**, present tense, imperative
   subject.
2. **Reference the ticket id in the body**, not the subject.
3. **Never commit unrelated changes together.**
4. **Do not commit or push unless the work builds and its tests
   pass.**

## What that looks like for real

The actual 4Notice history, newest first — thirteen days, eleven
commits:

```text
1fadaeb App icon and launch screen
9903739 Localize the UI into seven languages
2b452ae 14-day trial, then read-only; one-time unlock via StoreKit 2
d846a0e watchOS app: the four notes as read-only pages
1c10e02 Widgets for macOS and iOS, one per note
9469f74 macOS: quick access from the menu bar
15a742a Per-device font family and size
db22347 iPhone: one note at a time, swipe, pin as start note
b770b64 Sync notes through NSUbiquitousKeyValueStore with a size budget
422f971 Add rich text notes with a small format bar
ddcfa94 Add tickets N1–N13 from the basic app plan
```

The product's history is readable without opening a diff: each
subject states an outcome, each maps to a ticket. And inside:

```text
commit 422f971
Add rich text notes with a small format bar

Notes hold an AttributedString with codable intent attributes (bold,
italic, underline, heading); fonts are derived for display and never
stored. Format bar per note: B/I/U/H, bullet and checklist prefixes.

Ticket: n2-rich-text-editor
```

The body serves two purposes: it records the **design decision**
(intent attributes, fonts derived, never stored) where the next
reader will look for it, and the `Ticket:` line ties the change to
the scope, acceptance criteria, and Q&A that produced it. Commit →
ticket → plan: the complete why-chain of any line of code, three
hops, all in the repo.

## "Atomic" is a scope statement

Atomic doesn't mean small — the widgets commit touches many files.
It means **one meaningful step**: everything in the commit serves one
ticket's scope, and nothing else rode along. The payoff: a revert
removes exactly one feature, a bisect lands on one decision, a review
reads one thought.

Two rules protect this when an agent does the work:

- **No drive-by fixes.** An unrelated bug found mid-ticket becomes a
  ticket (or at least its own commit) — never part of an unrelated
  change.
- **Green before commit.** Rule 4 means the history contains no
  "WIP, tests broken" states — every commit checks out and builds.
  For 4Notice: `sh scripts/test.sh` before every commit, the same
  script the Test action runs.

## The second log

Commits track the *code*; the ticket **history** tracks the
*process* — an append-only JSONL per ticket where the agent logs
station moves, recorded answers, and skill runs
([details](/app/specs/)). When something looks odd later, the
two logs cross-check each other: what was done, and what was decided
while doing it.

With the working rhythm in place, the next chapters add leverage:
[importing skills](/tutorial/importing-skills/) so the agent doesn't
relearn solved problems — and exporting your own.
