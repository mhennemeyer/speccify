---
station: Doing
order: 7
created: 2026-09-11
needs_human: true
ready: false
open_question: Q1
parent: null
---
# Workspace-Board mit eindeutiger Projekt- und Worktree-Herkunft

## Why

V1-01 braucht nach der Erkennung aus 015 eine gemeinsame Spec-Sicht. Gleiche
Nummern in unabhängigen Repos und unterschiedliche Stände in Worktrees dürfen
nicht versehentlich verschmolzen werden.

## What

Lesendes Workspace-Board im Dashboard: alle Projekte oder Projektfilter,
Suche, Backlog/Doing/Done und unverändert benannte unbekannte Stationen.
Jede Karte zeigt Projekt, Repo und Worktree; Auswahl zeigt Inhalt und Dateipfad.
Ein expliziter Knopf öffnet das zugehörige bestehende Projektfenster.
Begrenztes Lesen, sichtbare Teilresultate und manuelles Aktualisieren.

Keine Drag-and-drop-/Task-/Editor-Mutationen im aggregierten Board. Keine Kopien
oder Migration von Specs. Kein Team-Sync (016), keine automatische Abnahme,
keine globale Spec-Nummernvergabe und keine Änderung laufender Terminals.
Skills/Playbooks sowie Dateien/Git bleiben im jeweils eigenen Projektfenster.

## Acceptance

- Zwei Repos mit identischer Spec-ID erscheinen als getrennte Karten mit Herkunft.
- Ein zusätzlicher Worktree zeigt seinen eigenen Stand; Gruppieren oder Umbenennen
  ändert Herkunftsnamen, nicht den Schlüssel einer ausgewählten Spec.
- Projektfilter und Suche begrenzen Board und Liste konsistent; Wechsel des
  Workspaces zeigt keine alten Karten oder Inhalte unter neuem Kontext.
- Änderungen an Quelldateien erscheinen nach Aktualisieren; fehlende,
  beschädigte, zu große oder verlinkte Quellen sind sichtbar statt still leer.
- Auswahl/Lesen/Öffnen verändert keine Spec und keinen Git-Index. Das Ziel des
  Öffnen-Knopfs ist der gewählte Worktree, nicht ein Repo mit gleicher Spec-ID.
- Lokale Einzelprojekt-Boards und die bisherigen Website-Motive bleiben erhalten.

## Decisions

- D1, 2026-09-11: Nutzer beauftragt Fortsetzung der Multiprojekt-Arbeit. Dieser
  Schnitt konkretisiert V1-01; 015 bleibt bereit zur menschlichen Abnahme geparkt.
- D2: Identität = Workspace-ID + Repo-ID + Worktree-ID + relativer Spec-Dateipfad.
  Projektgruppierung ist eine veränderliche Zuordnung, kein Bestandteil des Schlüssels.
  Kein Zusammenführen gleicher IDs über Worktrees oder Repos hinweg.
- D3: Bestehenden nativen Spec-Parser wiederverwenden. Alle Daten lokal und lesend;
  Snapshot mit Zeitpunkt, explizitem Refresh und Herkunft. Kein Teamstatus-Versprechen.
- D4: Öffnen führt ins Projektfenster; kein Versprechen, dort automatisch die
  ausgewählte Spec zu selektieren. Die genaue Datei ist vorher im Inspector sichtbar.

## Tasks

- [x] Begrenzten Aggregationsvertrag und Parser-Wiederverwendung implementieren.
- [x] Board, Liste, Filter, Suche und lesende Vorschau mit Herkunft ergänzen.
- [x] Kollisionen, Worktrees, Gruppierung, Fehlergrenzen und UI-Wechsel testen.
- [ ] Native Mac-App prüfen, Screenshot-Pflege sowie Playbooks/UI-Baum aktualisieren.
- [x] (added) Beim nativen Start belegte Main-Thread-Blockade der lesenden
  Workflow-Diagnose durch asynchronen Aufruf beheben; Diagnose-/Schreibvertrag erhalten.
  Code und Regression geprüft; nativer Neubau durch macOS-Datenschutzprüfung blockiert.

## Verification

- Skill-Suche `speccify search workspace`: kein Treffer. Vorhandene Workspace-
  Identitäten und Spec-Parser als Grundlage geprüft; keine fremde Domäne importiert.
- `cargo test -p speccify-desktop --offline`: zuletzt 82 bestanden, 2 bestehende Tests
  ignoriert. Drei neue Aggregationstests mit echten lokalen Git-Repos/Worktrees:
  gleiche IDs getrennt, gemeinsame Parser-Ergebnisse, stabile Schlüssel nach
  Gruppierung, Quelldatei-Refresh, Historie, unbekannte Station, fehlende Quellen,
  fehlerhafte/überlange Specs, Lesebudget und verlinkte Wissenspfade.
- Desktop-Typecheck und `cargo fmt --all --check` grün. Gemeinsamer Parser bleibt
  im nativen Projektvertrag; Einzelprojekt-Regressionen vollständig grün.
- `node scripts/test_workspace_board.mjs` und `node scripts/test_workspace_ui.mjs`
  grün: Filter/Liste, Vorschau, genaues Öffnen-Ziel, deaktivierte Markdown-Tasks,
  Refresh/Teilresultate/Fehler, unbekannte Stationen, schmale Hell-/Dunkelansicht,
  verzögerte Antwort beim Workspace-Wechsel. Bestehende fünf UI-Suites ebenfalls
  grün mit `PLAYWRIGHT_CHANNEL=chrome` (Playwright-Standardbrowser lokal fehlt).
- Skill `app-screenshots`: zweimal `pnpm screenshots:app`; erster Lauf mit
  abweichendem Skills-Raster, Wiederholung entspricht allen acht bisherigen PNGs.
  Keine Website-Bildänderung. Marketing-Build mit 93 Seiten und responsive
  Landingpage-/Features-Tests bei 1440/390/320 px einschließlich Ansicht ohne
  JavaScript grün. Neue Dashboard-Ansicht im Browser visuell geprüft.
- Lokaler Build: `./scripts/dev.sh --app --prepared --ui-port=18768` erfolgreich.
  Erster Kaltstart zeigt fünf leere Fenster. Prozess-Sample belegt blockierenden
  `workflow_setup::project_workflow_status` → `policy_state` → `open` auf dem
  Main-Thread, nicht den neuen asynchronen Workspace-Reader. Reguläre Aktivierung
  ohne Reaktion; ausschließlich diesen Startprozess per SIGTERM beendet und
  denselben Build mit `--open` erneut gestartet. Keine Systemfreigabe umgangen,
  keine Projektdatei oder gespeicherte Fensterliste geändert.
- Zweiter Start ebenfalls blockiert. Status-Command auf `spawn_blocking`
  umgestellt, gleiche synchrone Diagnose intern für Setup beibehalten. Neuer Test
  vergleicht beide Ergebnisse und belegt ausbleibende Projektdatei-Schreibzugriffe.
  Der volle Testlauf einschließlich dieser Korrektur ist grün (82/2).
- Neubau danach nicht ausgeführt: Schutzprüfung des Scripts meldet offene
  App-Binärdatei. `lsof` weist nur `tccd` (PID 665), nicht Speccify als Besitzer
  aus. Keine Umgehung der Schutzprüfung oder macOS-Freigabe, kein Beenden von
  Systemdiensten. Vorhandenen Build erneut mit `--open` geöffnet. Er enthält das
  Workspace-Board, aber noch nicht die nachfolgende asynchrone Startkorrektur.
  Bedienbarkeit und nativer Board-Durchlauf bleiben unbestätigt. Windows ungeprüft.

## Questions

### Q1 · open · 2026-09-11T05:45:37Z
Bitte prüfe am Mac, ob eine Datenschutzfreigabe für Speccify aussteht, insbesondere
für den Schreibtisch-/Projektordner, und bestätige die gewünschte Freigabe selbst.
`tccd` hält derzeit die App-Binärdatei offen und der gestartete Build zeigt leere
Fenster. Sobald die Prüfung freigegeben ist, finalen Build starten und das Board
mit dem gespeicherten Demo-Workspace nativ abnehmen. Keine Systemfreigabe umgehen.
