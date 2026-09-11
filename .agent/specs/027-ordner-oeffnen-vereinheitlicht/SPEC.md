---
station: Doing
order: 10
created: 2026-09-11
needs_human: true
ready: false
parent: null
---
# Ein Ordner öffnen: Einzelprojekt oder Workspace erkennt die App

## Why

Das Dashboard trennt das Öffnen bisher in zwei Wege: oben „Arbeitsordner →
Workspace erkennen“, darunter eingeklappt „Einzelprojekt direkt öffnen“. Der
Nutzer soll nicht vorher entscheiden müssen, ob ein Ordner ein Mono- oder ein
Multi-Repo-Projekt ist (BO, 2026-09-11).

## What

Ein einziger Einstieg „Ordner öffnen“ im Projekte-Tab: Pfad eingeben oder
wählen, öffnen. Die App klassifiziert den Ordner nativ und macht entsprechend
weiter:

- Der Ordner ist selbst ein Git-Repository → Einzelprojekt; das bestehende
  Projektfenster öffnet sich (wie bisher `project_open`).
- Der Ordner ist kein Repository, enthält aber mindestens ein erkanntes Repo
  oder Projekt (bestehende Workspace-Erkennung, Spec 015/025) → Workspace;
  er wird im lokalen Workspace-Store gespeichert bzw. aktualisiert und das
  gemeinsame Arbeitsfenster (Spec 026) öffnet sich.
- Weder noch → einfaches Einzelprojekt ohne Git; Projektfenster.

Gespeicherte Workspaces bleiben im Projekte-Tab sichtbar: Auswahl, erneut
erkennen, Gruppen bearbeiten, „Alle Specs“, Worktrees einzeln öffnen. Zuletzt
geöffnete Projekte bleiben als Liste. Das eigene Formular „Arbeitsordner“ und
der aufklappbare Einzelprojekt-Block entfallen.

Nicht enthalten: Änderungen am Workspace-Vertrag (Erkennung, Store, Gruppen),
neue Fenstertypen, Team-Sync, automatische Umzüge zwischen Einzelprojekt und
Workspace.

## Acceptance

- Wenn ein Ordner mit eigenem `.git` gewählt wird, dann öffnet sich sein
  Projektfenster, auch wenn er verschachtelte Repos oder Marker enthält.
- Wenn ein Ordner ohne eigenes `.git` gewählt wird, unter dem die Erkennung
  mindestens ein Repo/Projekt findet, dann erscheint er als gespeicherter
  Workspace, ist im Dashboard ausgewählt und sein Arbeitsfenster ist offen.
- Wenn ein Ordner ohne `.git` und ohne erkannte Unterprojekte gewählt wird,
  dann öffnet sich sein Projektfenster.
- Wenn der Pfad kein Verzeichnis ist, dann erscheint die bisherige
  Fehlermeldung und nichts wird gespeichert oder geöffnet.
- Die Mock-UI-Suiten für Workspaces und Workspace-Board laufen über den neuen
  Einstieg und prüfen, welches Fenster geöffnet wurde.

## Decisions

- D1, 2026-09-11: Ein Ordner mit eigenem Git-Repository ist immer ein
  Einzelprojekt. Grund: Repos enthalten häufig Fixtures, Submodule oder
  Beispielprojekte mit `speccify.yaml` (das Speccify-Repo selbst hat vier).
  Wer ein Repo mit seinen Submodulen als Workspace will, wählt den Elternordner.
- D2, 2026-09-11: Ein Workspace öffnet sofort sein gemeinsames Arbeitsfenster,
  symmetrisch zum Projektfenster. Gruppen werden weiterhin im Dashboard
  bearbeitet; dort ist der neue Workspace nach dem Öffnen ausgewählt.
- D3, 2026-09-11: Die Klassifikation nutzt die bestehende Erkennung ohne
  neue Domäne; `workspace_discover` bleibt für „Erneut erkennen“.

## Tasks

- [x] Nativer Command `folder_open`: klassifizieren, Projektfenster oder
      Workspace speichern + Arbeitsfenster öffnen; Ergebnis mit Art zurückgeben.
- [x] Rust-Test für die Klassifikation (Repo-Wurzel, Elternordner, leerer
      Ordner, Ordner mit Marker-Unterprojekt).
- [x] Projekte-Tab: ein Formular „Ordner öffnen“, Statusmeldung, zuletzt
      geöffnete Projekte; Workspace-Bereich ohne eigenes Formular, mit
      Auswahl des gerade geöffneten Workspace.
- [x] Mock-Fixture und UI-Suiten (`test_workspace_ui`, `test_workspace_board`)
      auf den neuen Einstieg umstellen.
- [x] Vertrag `docs/workspaces.md`, UI-Baum in `stand-und-ui.md`, In-App-Hilfe
      (`docs/app-bedienen.md`) anpassen.
- [ ] Website-Doku: „Open a folder“ im neuen Workspace-Kapitel beschreiben
      (added; läuft im Doku-Durchgang zum Release 0.7.0 mit).
- [x] Lokale App bündeln und neu starten; Wiederaufnahme prüfen.

## Verification

2026-09-11, Commit auf Basis `45a6b99`:

- `cargo test -p speccify-desktop`: 90 bestanden, 3 ignoriert; neuer Test
  `folder_kind_prefers_repo_root_then_nested_projects` deckt Repo-Wurzel mit
  verschachteltem Repo und Marker-Unterprojekt (→ Projekt), Elternordner mit
  zwei Repos (→ Workspace), leeren Ordner (→ Projekt) und Ordner mit
  `.agent/agent.md`-Unterprojekt (→ Workspace) ab; keine `.agent`-Schreibzugriffe.
  `cargo fmt --check` grün.
- `pnpm --filter speccify-desktop typecheck` grün.
- Browser-Suiten gegen `dev/mock.html` (Vite auf 127.0.0.1:1421): alle neun grün
  (`test_workspace_ui`, `test_workspace_board`, `test_workspace_shell`,
  `test_workspace_layout`, `test_spec_navigation`, `test_git_workspace`,
  `test_ui_colors`, `test_workflow_ui`, `test_action_output`). Die Workspace-Suite
  belegt: Elternordner → Statusmeldung „Workspace erkannt: 2 Repos/Ordner ·
  3 Worktrees“ + Arbeitsfenster-Ereignis; „/legacy“ → „Einzelprojekt erkannt“ +
  Projektfenster-Ereignis, auch über „Zuletzt geöffnete Projekte“; „/missing“ →
  Fehlermeldung ohne Öffnen-Ereignis. Fünf Suiten benötigten zuvor
  `pnpm exec playwright install chromium` (fehlende Headless-Shell nach
  Playwright-Update, unabhängig von dieser Änderung).
- Lokale App: mit ⌘Q-äquivalentem Quit beendet, `./scripts/dev.sh --app
  --prepared --skip-engine --ui-port=18768` neu gebündelt und gestartet; Prozess
  läuft, Desktop-UI-MCP `initialize` antwortet 200 (`speccify-desktop-ui-mcp`).
- Nicht geprüft: nativer Klick-Durchlauf mit echten Ordnern (der Desktop-UI-MCP
  bietet nur `ask_bo`); bleibt Teil der menschlichen Abnahme. Windows ungetestet.

## Questions
