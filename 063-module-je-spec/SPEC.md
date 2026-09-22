---
station: Doing
order: 63
created: 2026-09-22
modules: board, workflow-policy, docs
---
# Module je Spec: parallel arbeiten ohne Kollisionen

## Why

BO 2026-09-22: Mehrere Agenten sollen gleichzeitig an einem System arbeiten.
Dafür muss sichtbar sein, welche Module eine Spec anfasst — Agent 2 soll merken,
dass Modul X gerade von Agent 1 (Spec 3) bearbeitet wird. Und beim Zuschnitt
sollen Specs möglichst wenige Module berühren; das setzt eine Architektur-Idee
voraus, die Module benennt. Das gilt für die heutige App, unabhängig von der
Container-Neuausrichtung (062), und soll dem Kollegen sofort per Release zur
Verfügung stehen.

## What

- Frontmatter `modules: a, b` je Spec (flach, kommagetrennt; `null`/leer = keine).
- Modulkatalog des Projekts in `.agent/settings.json` unter `modules`
  (`name`, `description`, optional `paths`): die Architektur-Idee, gegen die
  Specs geschnitten werden. Pflege in der App (Board-Kopf „Module…“).
- Board: Karten zeigen Module; überschneidet sich ein Modul mit einer **anderen**
  Spec in Doing, trägt die Karte einen Hinweis („Modul X · auch #12“). Der
  Inspektor nennt je Modul die Kollision und markiert Module, die nicht im
  Katalog stehen. Editor-Sheet mit Modul-Feld (Vorschläge aus dem Katalog).
- Workflow-Policy v11: Modulfeld pflegen, vor Start Überschneidung mit Doing
  prüfen und melden, beim Zuschnitt Module minimieren, ohne Modulliste zuerst
  eine vorschlagen/nachfragen.
- Doku (specs.md), Release 0.8.5.
- Außerhalb: Sperren oder Verhindern (die App zeigt, sie verbietet nicht),
  Workspace-Board-Karten, Web-Board/MCP-Felder, automatische Modulerkennung
  aus Pfaden, Umbau bestehender Specs.

## Acceptance

- Wenn eine Spec `modules: terminal, board` trägt, dann zeigt ihre Karte beide
  Module und der Inspektor listet sie.
- Wenn zwei Specs in Doing dasselbe Modul nennen, dann tragen beide Karten
  einen Kollisionshinweis mit der jeweils anderen Nummer; eine Backlog-Spec mit
  demselben Modul zeigt den Hinweis ebenfalls (vor dem Start sichtbar).
- Wenn ein Modul nicht im Katalog steht, dann markiert der Inspektor es als
  unbekannt; ohne Katalog erscheint der Hinweis, einen anzulegen.
- Wenn im Sheet Module eingetragen werden, dann steht `modules:` im Frontmatter;
  leer entfernt die Zeile; andere Zeilen bleiben byte-stabil.
- Wenn der Katalog im Board gepflegt wird, dann steht er unter `modules` in
  `.agent/settings.json` (versioniert, teamweit).
- Wenn „Einrichten“ läuft, dann trägt `agent.md` Policy v11 mit dem Modul-Abschnitt.

## Decisions

1. 2026-09-22: Katalog in `.agent/settings.json` (`modules`), nicht in einem
   Playbook — maschinenlesbar, neben `board.*`, teamweit versioniert. Eine
   Architektur-Beschreibung in Prosa kann zusätzlich als Playbook existieren.
2. 2026-09-22: Kollision = gleiches Modul in einer anderen Spec in Doing.
   Done zählt nicht; Backlog-Specs zeigen den Hinweis, damit er vor Backlog→Doing
   sichtbar ist. Die App warnt nur; Regel und Entscheidung liegen beim Menschen.
3. 2026-09-22: Modulnamen wie Slugs (`[a-z0-9-]`), Vergleich case-insensitiv.
   Unbekannte Module sind erlaubt (Hinweis), damit ein Agent ein neues Modul
   eintragen kann, bevor der Katalog nachgezogen ist.
4. 2026-09-22: `modules` ist ein Feld, das der Agent bearbeiten darf (anders als
   `owner`/`branch`): Wer ein Modul anfasst, das nicht in der Spec steht, trägt
   es nach.

## Tasks

- [ ] Rust: `modules` parsen (`TicketEntry`), Anlegen/Speichern mit Modul-Feld, Tests.
- [ ] Policy v11 (Template, History v10, `WORKFLOW_VERSION`, eigene `agent.md`, Spec-Vorlage).
- [ ] Frontend: Modul-Chips und Kollisionshinweis auf Karten, Inspektor-Zeile, Sheet-Feld, Katalog-Sheet im Board-Kopf, `lib/modules.ts`.
- [ ] Mock-Fixture `?modules=1` und Browser-Regression `test_spec_modules.mjs`.
- [ ] Doku: `specs.md`, Release-Notes 0.8.5, Landing-Link, Playbooks `stand-und-ui`/`weiterentwicklung`.
- [ ] Checks (project-checks), Commit, Release 0.8.5 nach Skill `release` (eigene Spec).

## Verification

Noch nichts ausgeführt.

## Questions
