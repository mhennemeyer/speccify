---
station: Doing
order: 42
needs_human: true
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

- [ ] Register-Bedienung mit Zielkennzeichnung und Fehleranzeige integrieren.
- [ ] Mehrere Repositories, Einrichtung und Statuswechsel gezielt prüfen.
- [ ] Playbooks und Workspace-Dokumentation aktualisieren.
- [ ] Lokale App aktualisieren und AVC-Anzeige prüfen; committen/pushen.

## Verification

Vor Änderung: App 0.7.0 läuft; native Statusabfrage liefert migratable für
billi-ci und rekas, none für AVC und billi-legacy. Kein data-register im
AVC-Workspace. Keine Änderungen an AVC vorgenommen.

## Questions

Keine.
