---
title: Arbeiten & atomare Commits
description: "Stetiger Fortschritt, den man auditieren kann: ein bedeutsamer Schritt, ein Commit."
sidebar:
  order: 5
---

Ein Agent produziert schnell viel Änderung. Commit-Disziplin hält
diese Änderung auditierbar — vier Regeln aus dem Workflow-Vertrag
(`agent.md`):

1. **Ein Commit pro bedeutsamem Schritt**, Präsens, imperatives
   Subject.
2. **Ticket-Id in den Body**, nicht ins Subject.
3. **Nie zusammenhanglose Änderungen zusammen committen.**
4. **Nicht committen oder pushen, solange der Stand nicht baut und
   seine Tests nicht bestehen.**

## Wie das real aussieht

Die tatsächliche 4Notice-Historie, neueste zuerst — dreizehn Tage,
elf Commits:

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

Die Produkthistorie ist lesbar, ohne einen Diff zu öffnen: Jedes
Subject benennt ein Ergebnis, jedes gehört zu einem Ticket. Und
innen:

```text
commit 422f971
Add rich text notes with a small format bar

Notes hold an AttributedString with codable intent attributes (bold,
italic, underline, heading); fonts are derived for display and never
stored. Format bar per note: B/I/U/H, bullet and checklist prefixes.

Ticket: n2-rich-text-editor
```

Der Body erfüllt zwei Zwecke: Er hält die **Designentscheidung**
fest (Intent-Attribute, Fonts abgeleitet, nie gespeichert) — genau
dort, wo der nächste Leser suchen wird — und die `Ticket:`-Zeile
verknüpft die Änderung mit Scope, Akzeptanzkriterien und Q&A, die
sie hervorgebracht haben. Commit → Ticket → Plan: die vollständige
Warum-Kette jeder Codezeile, drei Sprünge, alles im Repo.

## „Atomar" ist eine Aussage über den Umfang

Atomar heißt nicht klein — der Widgets-Commit fasst viele Dateien an.
Es heißt **ein bedeutsamer Schritt**: Alles im Commit dient dem Scope
eines Tickets, und nichts anderes ist mitgefahren. Der Nutzen: Ein
Revert entfernt genau ein Feature, ein Bisect landet auf einer
Entscheidung, ein Review liest einen Gedanken.

Zwei Regeln schützen das, wenn der Agent die Arbeit macht:

- **Keine Drive-by-Fixes.** Ein fremder Bug, mitten im Ticket
  gefunden, wird ein Ticket (oder mindestens ein eigener Commit) —
  nie Teil einer fremden Änderung.
- **Grün vor dem Commit.** Regel 4 heißt: Die Historie enthält keine
  „WIP, Tests kaputt"-Zustände — jeder Commit lässt sich auschecken
  und bauen. Für 4Notice: `sh scripts/test.sh` vor jedem Commit —
  dasselbe Skript, das die Test-Aktion ausführt.

## Das zweite Protokoll

Commits verfolgen den *Code*; die Ticket-**History** verfolgt den
*Prozess* — ein append-only-JSONL pro Ticket, in das der Agent
Stationswechsel, festgehaltene Antworten und Skill-Läufe loggt
([Details](/de/app/board/)). Wenn später etwas seltsam
aussieht, prüfen sich die beiden Protokolle gegenseitig: was getan
wurde, und was dabei entschieden wurde.

Mit dem Arbeitsrhythmus an Ort und Stelle bringen die nächsten
Kapitel Hebelwirkung:
[Skills importieren](/de/tutorial/importing-skills/), damit der Agent
gelöste Probleme nicht neu lernt — und eigene exportieren.
