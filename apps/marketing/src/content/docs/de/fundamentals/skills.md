---
title: Skills
description: Wiederverwendbare Anweisungen für den Agenten — ein Ordner pro Skill, eine SKILL.md als Quelle der Wahrheit.
sidebar:
  order: 2
---

Ein **Skill** ist ein wiederverwendbares Anweisungspaket für den
Agenten: wie die Release-Checks laufen, wie das nächste Ticket gewählt
wird, wie eine Frage an den Owner geht. Jeder Skill ist ein Ordner
unter `.agent/skills/` mit einer `SKILL.md` — das Frontmatter sagt,
*wann* er greift, der Body sagt, *wie*.

## Ein minimaler, echter Skill

Das ist `ticket-next` — der Skill, der das Board antreibt, wörtlich:

```markdown
---
name: ticket-next
description: Pick the next backlog ticket, move it to In Progress and work it
  to completion. Use when the user says "next ticket", "weiter", or asks
  what to work on.
---

Follow the board workflow in `.agent/agent.md`.

1. Read `.agent/board/*.md`. Refuse to start if a ticket is already in
   `In Progress` — finish or split that one first.
2. Pick the `Backlog` ticket with the lowest `order`.
3. Set `station: In Progress`, then implement it.
4. Verify against the ticket's acceptance criteria before setting
   `station: Done`.

If a decision is needed that only the owner can make, use the
`ticket-ask` skill instead of guessing.
```

Zwei Dinge fallen auf:

- Die **description** ist für die Auslöse-Entscheidung des Agenten
  geschrieben: Sie benennt die Situationen („next ticket", „weiter"),
  in denen der Skill gilt. Eine vage Description bedeutet: Der Skill
  feuert nie.
- Der **Body** ist eine Prozedur mit Verweigerungsbedingung und
  Verifikationsschritt — keine Prosa über das Thema. Skills, die wie
  Artikel klingen, werden überflogen; Skills, die wie Checklisten
  klingen, werden befolgt.

## Anatomie eines größeren Skills

Produktions-Skills bekommen ein paar Teile mehr. `release-checks`
(aus dem Speccify-App-Projekt) prüft ein App-Bundle vor dem
App-Store-Upload; seine Struktur lohnt das Kopieren:

```markdown
---
name: release-checks
description: Pre-release checks for a sandboxed Apple app bundle —
  entitlements, Info.plist usage keys and localization leftovers that
  App Review would ask about. Use before tagging a release, before an
  App Store upload, or when asked whether the bundle is clean.
license: MIT
compatibility: macOS with Xcode command line tools (codesign) and python3.
---

Three tools do the looking; each takes one JSON object on stdin and
answers with one JSON object on stdout (the contract is the `TOOL.md`
beside each). The tools only make lists visible — deciding what
belongs is the reviewer's job, and the answer is a short report,
never a silent fix.

## 1 — Entitlements of the built bundle
...run [check-entitlements](../../tools/check-entitlements/TOOL.md)...
**Verify:** the list contains only entitlements you can name a feature for.

## 2 — Usage descriptions and background modes
...

## Pitfalls
- Running step 1 on a Debug build with different entitlements than
  the Release configuration — check the bundle you will ship.
...

## In this project
- Bundle: build with `sh scripts/app-build.sh`; ...
```

Die wiederkehrenden Teile:

- **Schritte, jeder mit einer `Verify:`-Zeile** — der Agent weiß,
  wann ein Schritt fertig ist, nicht nur, was zu tun ist.
- **Links auf [Tools](/de/fundamentals/tools/)** als relative Pfade
  (`../../tools/<name>/`) — der Skill *entscheidet und berichtet*,
  das Tool *misst*. Urteil im Skill, Mechanik im geprüften Tool: das
  ist die zentrale Arbeitsteilung.
- **Ein `Pitfalls`-Abschnitt** — Fehler, die der Autor des Skills
  schon gemacht hat, damit der Agent sie nicht wiederholt.
- **Ein `In this project`-Abschnitt** — die generische Prozedur
  bleibt wiederverwendbar; projektspezifische Pfade und Erwartungen
  stehen am Ende.

## Wo Skills liegen — und warum Symlinks

`.agent/skills/` ist die **Quelle**. Agent-Produkte erwarten eigene
Ordner (Claude Code liest `.claude/skills/`), also sind das Symlinks:

```text
.claude/skills → ../.agent/skills
```

Einen Skill unter `.agent/skills/` anlegen oder ändern — und jeder
Agent sieht die Änderung sofort. Nie in einem Dot-Ordner editieren:
Die Änderung landet ohnehin in derselben Datei — oder zerstört den
Link. Skills können auch aus einer Speccify-Quelle
installiert werden; wie das funktioniert, steht in der
[Speccify-Section](/de/speccify/overview/).
