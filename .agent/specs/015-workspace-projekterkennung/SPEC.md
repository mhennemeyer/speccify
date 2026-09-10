---
station: Backlog
order: 7
created: 2026-09-10
needs_human: true
ready: false
parent: null
---
# Workspace öffnen, Repos erkennen und Projekte gruppieren

## Why

Ein geöffneter Arbeitsordner kann mehrere Repositories enthalten. Die App muss
deren Grenzen sichtbar machen und anpassbare fachliche Gruppierung erlauben.
Bestätigte Entscheidung D-MR-01 zu V1-01 im
[Visionsplaybook](../../playbooks/weiterentwicklung.md).

## What

Erster vertikaler Schnitt: begrenzte read-only Repository-Erkennung, eindeutiges
Workspace-/Projekt-/Repo-/Worktree-Modell und eine Auswahl-/Gruppierungsoberfläche.
Jedes erkannte Repo wird zunächst als eigenes Projekt angeboten. Gruppieren und
Entgruppieren ändern Zuordnungen, nicht Dateien oder Git-Zustand der Repos.
Die Auswahl führt in die bestehenden projektbezogenen Ansichten mit eindeutigem Ziel.

Identitäten bleiben bei Umbenennung/Umgruppierung stabil. Eine persistierte
Zuordnung trennt gemeinsame IDs von lokalen Pfaden; Format und Speicherort
werden vor Implementierung als kleiner Vertrag festgelegt. Keine zweite
Domänenimplementierung für CLI/MCP/Desktop.

Nicht Teil dieses Schnitts: gemeinsames Team-Sync, automatische Migration von
Specs/Skills, Zusammenführen gleichnamiger Dateien, Sprachdienste oder fremde
Workflow-Schreibadapter. Aggregiertes Board und durchgängige Herkunfts-Badges
bleiben weitere Schnitte von V1-01 und werden hier nicht als fertig ausgegeben.

## Acceptance

- Ordner mit zwei Git-Repos öffnen: beide zunächst getrennt sehen und öffnen.
- Zwei Repos gruppieren, App neu öffnen, Zuordnung wiederfinden und auflösen;
  Repo-Dateien und Git-Index bleiben unverändert.
- `.git` als Datei, zusätzlicher Worktree und verschachteltes Repo werden
  nachvollziehbar erkannt; derselbe Git-Ursprung wird nicht versehentlich dupliziert.
- Ignorierte Abhängigkeits-/Buildordner und Symlink-Schleifen führen weder zu
  unbeschränkter Suche noch Schreibzugriffen außerhalb des gewählten Arbeitsverbunds.
- Vorhandene Einzelprojekte und Ordner ohne Git bleiben nutzbar; Öffnen führt
  nicht automatisch `git init` oder Workflow-Einrichtung aus.
- Projektwechsel benennt den Zielkontext, ohne ein bereits laufendes Terminal
  still in ein anderes Repo umzulenken.

## Decisions

- D1, 2026-09-10: D-MR-01 ausdrücklich bestätigt: Repos zunächst einzeln, Gruppierung frei anpassbar.
- D2: Gruppierung ist keine Freigabe zur Verschmelzung von `.agent`-Inhalten.
- D3: Bestehende Konsistenzarbeiten 008/011 berücksichtigen; IDs mit Spec 016 abstimmen.
- D4: Keine neue laufende App-Instanz oder automatischer Neustart für diese Planung.

## Tasks

- [ ] Identitäts-/Zuordnungsvertrag und Fixture-Matrix festlegen.
- [ ] Begrenzte Repository-/Worktree-Erkennung implementieren und negativ testen.
- [ ] Auswahl, Gruppierung und Persistenz in einem UI-Schnitt umsetzen.
- [ ] Bestehende Projektansichten mit eindeutigem Ziel weiterverwenden.
- [ ] Abnahme in Wegwerf-Workspace durchführen und Ist-/UI-Playbook aktualisieren.

## Verification

- Planungsprüfung: D-MR-01 ins Playbook übernommen, Schnitt und Ausschlüsse benannt.
- Speccify-Skill: Bibliothekssuche nach `workspace` ohne Treffer; bestehendes
  Spec-Format verwendet. Noch keine Funktionsimplementierung oder App-Abnahme.

## Questions

- Speicherformat und Detaildarstellung sind technische Entwurfsarbeit; bei
  Auswirkungen auf bereits vorhandene Projektdateien Migration vorher separat entscheiden.
