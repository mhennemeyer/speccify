---
station: Doing
order: 12
created: 2026-09-12
needs_human: true
ready: true
open_question: null
parent: null
---
# Team-Board im Web: Fortschritt beobachten, ohne die App zu öffnen

## Why

Das Team (und wer sonst zuschauen darf) soll den Fortschritt aller Specs im
Browser sehen — Stationen, Tasks, wer woran arbeitet, wie viel Bewegung es
gibt — ohne Speccify zu starten oder ein Repo zu klonen. Nutzerauftrag vom
2026-09-12: „schau ob wir eine Team-WebApp erstellen können. Hauptfeature:
Progress beobachten.“ Grundlage ist das gemeinsame Register aus
[028](../028-spec-branch-als-register/SPEC.md): der Branch `specs` ist
bereits die Wahrheit, die alle teilen.

## What

Eine **statische Board-Seite**, erzeugt aus dem Spec-Register: `speccify
board` (Python-Core `board.py`, CLI-Adapter) liest `.agent/specs` bzw. den
Checkout des Branch `specs` und schreibt eine in sich geschlossene HTML-Seite
ohne externe Abrufe. Inhalt: Kennzahlen (Tasks erledigt gesamt mit Balken,
Backlog/Doing/Done, bereit zur Abnahme, offene Fragen, Agent-Läufe in 30
Tagen), Aktivität der letzten 30 Tage als Balken (Läufe, Stationswechsel),
„Doing nach Person“ (aus `owner`, Spec 029), das Board in drei Spalten mit
Fortschrittsbalken, Besitzer-Initialen, Branch, Flags (bereit, braucht
Abnahme, Frage, Idee) und Alter der letzten Aktivität, Suche und Filter per
Inline-JS; Altbestand eingeklappt.

Veröffentlichung für das Speccify-Repo selbst: der Pages-Workflow baut die
Seite bei jedem Push auf `specs` (und `main`) und liefert sie unter
`speccify.io/board/` aus; die Website verlinkt sie in der Navigation. Für
private Team-Repos läuft derselbe Befehl in deren CI oder lokal und die Seite
liegt auf einem internen Host.

Nicht enthalten: ein Dienst mit Login, Schreibzugriff aus dem Browser,
Echtzeit-Push (Aktualität = Push-Frequenz auf `specs`, wenige Minuten),
Aggregation mehrerer Repos, ein Client, der GitHub direkt mit Token liest.
Diese drei sind Kandidaten für Folgeschnitte (siehe Decisions).

## Acceptance

- Wenn `speccify board --project <repo>` läuft, dann entsteht eine HTML-Datei,
  die ohne Netz und ohne Server im Browser funktioniert und dieselben Zahlen
  zeigt wie das Board der App (Stationen, Tasks je Spec, Besitzer, Branch,
  Flags, Altbestand getrennt).
- Wenn ein Push auf `specs` erfolgt, dann ist die Seite unter `/board/`
  innerhalb eines Deploy-Laufs aktualisiert und nennt den Register-Commit.
- Wenn der Branch `specs` fehlt, dann baut die Website ohne Board und
  scheitert nicht.
- Wenn in der Seite gesucht oder nach Person/Flag gefiltert wird, dann
  verschwinden nicht passende Karten und die Spaltenzähler folgen.
- Wenn eine Spec keine Tasks hat, dann zeigt sie keinen Balken; Done zählt als
  vollständig.

## Decisions

- D1, 2026-09-12: Statische Seite aus dem Register statt Dienst. Grund: keine
  Auth, kein Betrieb, kein Offline-Problem; das Register ist schon die geteilte
  Wahrheit; „beobachten“ braucht Minutenaktualität, keine Echtzeit.
- D2, 2026-09-12: Generator im Python-Core (`speccify_core.board`), CLI als
  dünner Adapter — gleiche Lesart wie die App (flaches Front Matter, Checkboxen
  außerhalb von Code-Blöcken, `history.jsonl`).
- D3, 2026-09-12: Deploy als Teil des bestehenden Pages-Workflows (ein
  Deployment, kein zweiter Pages-Pfad); der Build holt `origin/specs` lesend.
- D4, 2026-09-12: Archivordner tragen Datumsnamen, keine laufende Nummer;
  das Board zeigt für Altbestand keine Nummer und klappt ihn ein.
- D6, 2026-09-12: GitHub führt Push-Workflows nur aus, wenn die Datei im
  gepushten Branch liegt. Deshalb liegt ein Mini-Workflow im Branch `specs`,
  der den Deploy auf main per `workflow_dispatch` anstößt; `pages.yml` selbst
  bleibt auf main und liest `origin/specs` nur.
- D5, 2026-09-12: Folgeschnitte, nicht Teil dieser Spec: (a) mehrere Repos in
  einer Seite (Workspace-Sicht), (b) Browser-Client mit GitHub-Token für
  private Repos ohne CI, (c) Burn-up je Ober-Spec.

## Tasks

- [x] Core `board.py`: Specs, Tasks, History laden; Zusammenfassung; HTML.
- [x] CLI `speccify board` (`--out`, `--specs`, `--project`, `--title`,
      `--source`, `--no-archive`); CLI-Referenz regeneriert.
- [x] Tests: Parser, Zusammenfassung, Seite (Core) und CLI.
- [x] Pages-Workflow: Trigger auf `specs`, Board aus `origin/specs` bauen,
      Navigationslink „Board“, generierte Datei ignoriert.
- [x] Deploy beobachten: `speccify.io/board/` nach dem nächsten Push prüfen
      (Link-Check der Site im PR-Workflow darf `/board/` nicht als tot werten).
      Live mit `specs@2659f3a`; Docs-Workflow inkl. Link-Check grün.
- [x] Trigger aus dem Register: `.github/workflows/board.yml` im Branch `specs`
      stößt `pages.yml` auf main per `workflow_dispatch` an (added, D6).

## Verification

2026-09-12:

- `pytest core cli tests`: 66 bestanden (neu: Front Matter/Task-Regeln inkl.
  Code-Blöcke, Laden mit Feldern/Tasks/History/Archiv, Zusammenfassung mit
  Personen und 30-Tage-Aktivität, Seite ohne externe URLs mit Balken/Badges;
  CLI schreibt Datei und meldet Zahlen, ohne Specs-Ordner Exit 1). `ruff check`
  und `ruff format --check` grün; `scripts/gen_cli_docs.py --check` grün.
- Echter Lauf auf diesem Repo (`specs@…`): 30 Specs, 132/163 Tasks, Backlog 7 ·
  Doing 20 · Done 3, Altbestand 32 eingeklappt; Screenshot geprüft (Kennzahlen,
  Aktivitätsbalken, Doing nach Person, drei Spalten mit Balken). Suche
  „register“ zeigt 2 Karten, Filter „bereit“ 18.
- Deploy geprüft: `Deploy site` und `Docs & Marketing Site` (mit Link-Check)
  grün; `https://speccify.io/board/` antwortet 200 und nennt `specs@2659f3a`.
  Der erste Push auf `specs` ohne Workflow-Datei im Branch löste keinen Lauf aus
  → D6. Offen: der Lauf des Board-Triggers selbst (Sichtprüfung nach dem
  nächsten Push) und Deine Sicht auf die Seite. Deshalb `ready`.

## Questions

Keine.
