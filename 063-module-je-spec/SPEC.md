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

- [x] Rust: `modules` parsen (`TicketEntry`), Anlegen/Speichern mit Modul-Feld, Tests.
- [x] Policy v11 (Template, History v10, `WORKFLOW_VERSION`, eigene `agent.md`, Spec-Vorlage).
- [x] Frontend: Modul-Chips und Kollisionshinweis auf Karten, Inspektor-Zeile, Sheet-Feld, Katalog-Sheet im Board-Kopf, `lib/modules.ts`.
- [x] Mock-Fixture `?modules=1` und Browser-Regression `test_spec_modules.mjs`.
- [x] Doku: `specs.md`, Release-Notes 0.8.5, Landing-Link, Playbooks `stand-und-ui`/`weiterentwicklung`.
- [x] Checks (project-checks), Commit.
- [ ] Release 0.8.5 nach Skill `release` → Spec 064.

## Verification

2026-09-22, Umgebung macOS (Apple Silicon), Chrome über Playwright, Vite-Mock
auf 127.0.0.1:5199.

- `cargo test -p speccify-desktop`: 134 passed, 3 ignored (davon neu: Modul-
  Parsing in `board_reads_specs_and_moves_byte_stable`, Anlegen/Speichern in
  `create_save_history_and_kpis_roundtrip`, Policy-Version in
  `workflow_setup`). `cargo fmt --check` ohne Befund.
- `pnpm --filter speccify-desktop typecheck` ohne Befund.
- Browser: `test_spec_modules` ok (Chips, Überschneidung Doing↔Doing und
  Backlog↔Doing, Done ohne Hinweis, Inspektor „nicht im Katalog“ und „auch in
  Doing: #12 …“, Sheet-Feld vorbelegt, Katalog-Dialog: Vorschlag übernehmen,
  speichern → `projectSettings.modules` mit drei Einträgen, ungültiger Name
  abgewiesen, `?modules=nocatalog` → „Module…“ und Hinweis im Inspektor).
  Gegen den alten `BoardTab.tsx` schlägt die Suite fehl (Schritt unten).
  Nachbarn grün: `test_board_done_window`, `test_spec_navigation`,
  `test_spec_owner`, `test_spec_register`, `test_workspace_board`,
  `test_team_signals` (je exit 0).
- Python: 287 passed, 1 deselected; ruff check/format ohne Befund;
  `speccify verify` ok (drei Tools ohne macOS-Implementierung, kein Drift).
- `pnpm marketing:build`: `/releases/0-8-5/` und `/de/releases/0-8-5/` gebaut.
- Eigene `agent.md`: Block v11 identisch zur Vorlage; Katalog für dieses Repo
  noch nicht angelegt (`.agent/settings.json` fehlt) — bewusst offen, damit BO
  die Modulliste bestätigt, statt dass der Agent sie setzt (Policy v11).
- Nicht geprüft: Klick-Abnahme in der gebündelten App (kommt mit dem Update auf
  0.8.5, Spec 064); Workspace-Board und Web-Board zeigen Module nicht.

## Questions
