---
station: Doing
order: 42
needs_human: true
ready: true
---

# Team-Register im Workspace einrichten und prüfen

## Why

AVC ist der erste reale Team-Pilot. Die App erkennt billi-ci und rekas als
bereit für ein gemeinsames Spec-Register, zeigt den Einrichtungsvorschlag aber
nur im Einzelprojektfenster. Im Workspace fehlen Einrichtung und Sync-Status.

## What

Bestehende Register-Bedienung im Workspace-Board zugänglich machen, pro
verfügbarem Worktree mit eindeutigem Repository und Pfad. Einrichtung,
Einhängen, Sync, Fehler und Konfliktentscheidung wiederverwenden.
AVC-Repositories nicht automatisch migrieren; Änderungen erfolgen erst durch
die bestehende konkrete Einrichtung im UI.

## Acceptance

- Im AVC-Workspace erscheinen Einrichtungsvorschläge für billi-ci und rekas.
- Einrichten und Sync betreffen nur das im Dialog gekennzeichnete Ziel.
- Fehlende/ausgeblendete Ziele bieten keine Register-Schreibaktion an.
- Fehler, vorhandene Register und Konflikte sind im Workspace sichtbar.
- Nach dem lokalen Update bleiben Fenster und Arbeitskontext erhalten.

## Decisions

1. 2026-09-15: Direkter Nutzerauftrag zur Behebung. Bestehenden RegisterBar
   wiederverwenden; keine zweite Migration oder Sammelaktion implementieren.
2. 2026-09-15: AVC ist kein Git-Repository. Jedes enthaltene Code-Repository
   trägt seinen eigenen specs-Branch; das gemeinsame Board aggregiert diese.

## Tasks

- [x] Register-Bedienung mit Zielkennzeichnung und Fehleranzeige integrieren.
- [x] Mehrere Repositories, Einrichtung und Statuswechsel gezielt prüfen.
- [x] Playbooks und Workspace-Dokumentation aktualisieren.
- [ ] Lokale App aktualisieren und AVC-Anzeige prüfen; committen/pushen.

## Verification

Vor Änderung: App 0.7.0 läuft; native Statusabfrage liefert migratable für
billi-ci und rekas, none für AVC und billi-legacy. Kein data-register im
AVC-Workspace. Keine Änderungen an AVC vorgenommen.

- `pnpm --filter speccify-desktop typecheck`: grün. Lokaler signierter App-Build
  mit `dev.sh --app --prepared --skip-engine --ui-port=18768 --qa-bridge=18769`
  erfolgreich; alle vier Fenster wiederhergestellt, App-PID 15577.
- `test_workspace_register.mjs`: Einrichtung mit Bestätigung/Abbruch, Fehler und
  Wiederholung, Einhängen/Sync, gezielte Konfliktentscheidung, Statusfehler und
  ausgeblendete/nicht verfügbare Ziele grün. Normale und schmale Demo-Ansicht
  visuell geprüft. Registerbereich scrollt separat, Board bleibt zugänglich.
- `test_spec_register.mjs` und `test_workspace_shell.mjs`: grün; Einzelprojekt-
  Register, Datei-/Commit-Entwürfe, gemeinsames Terminal und Zielbindung erhalten.
- Nativer Test `/private/tmp/speccify_042_native.py`: zwei temporäre Repos mit
  lokalen Bare-Remotes; Migration von alpha lässt beta unverändert, specs/main
  werden gepusht, Spec-Inhalt bleibt erhalten. Frischer Klon meldet detached,
  Einhängen gelingt, anschließend Spec-Fortschritt per Sync in beiden Klonen
  identisch, Code-Checkouts sauber. Kein externes Remote beteiligt.
- Native AVC-UI zeigt genau zwei migratable-Register mit Button und Pfad:
  billi-ci und rekas. AVC und billi-legacy bieten keine Migration an.
  Bildschirmaufnahme über die native QA-Route war nicht verfügbar (HTTP 500);
  native Anzeige per DOM und echte Befehle geprüft, Optik mit Browser-Fixture.
- Marketing-Build: 101 Seiten, Doku-Sync und `git diff --check` grün.

## Questions

Keine.
