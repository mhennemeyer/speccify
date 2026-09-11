---
station: Doing
order: 7
created: 2026-09-10
needs_human: true
ready: true
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
- D5, 2026-09-11: Nutzer beauftragt Umsetzung. Nativer Workspace-Vertrag in
  docs/workspaces.md; keine parallele Python-Domäne. Zufällige persistierte IDs,
  lokale Pfadbindungen und Gruppierungen getrennt. Anzeigenamen/Zuordnungen
  ändern keine IDs. Dateisystem-Umzüge werden nicht aus Namen geraten.
- D6: Erkennung nur im gewählten Baum, ohne Symlink-Verfolgung oder Git-Kommandos;
  .git-Datei/commondir identifizieren gemeinsame Repos. Verknüpfte Worktrees
  außerhalb des gewählten Baums nicht automatisch öffnen oder durchsuchen.
- D7: Neuer Dashboard-Workspace-Bereich; einzelne Worktrees öffnen weiterhin
  eigene Projektfenster. Keine Umleitung laufender Terminals. Lokale Zuordnung
  atomar und revisionsgeprüft speichern; beschädigte Datei nicht überschreiben.
- D8: D4 betraf nur Planung; für diese Umsetzung gilt die stehende Erlaubnis zum
  angekündigten App-Update mit anschließendem Neustart und Wiederherstellungsprüfung.

## Tasks

- [x] Identitäts-/Zuordnungsvertrag und Fixture-Matrix festlegen.
- [x] Begrenzte Repository-/Worktree-Erkennung implementieren und negativ testen.
- [x] Auswahl, Gruppierung und Persistenz in einem UI-Schnitt umsetzen.
- [x] Bestehende Projektansichten mit eindeutigem Ziel weiterverwenden.
- [x] Technischen Abnahmelauf in Wegwerf-Workspace durchführen und Ist-/UI-Playbook aktualisieren.
  Menschliche Produktabnahme bleibt als `needs_human: true` offen.

## Verification

- Planungsprüfung: D-MR-01 ins Playbook übernommen, Schnitt und Ausschlüsse benannt.
- Speccify-Skill: Bibliothekssuche nach `workspace` ohne Treffer; nativen Vertrag
  in `docs/workspaces.md` implementiert, keine zweite Python-Domäne eingeführt.
- 2026-09-11: `cargo test -p speccify-desktop --offline`: 78 bestanden,
  2 bestehende Tests ignoriert. Sechs neue Workspace-Tests: echte Git-Repos,
  Worktree-/Submodule-Pointer, verschachtelte Repos, externe Common-Metadaten,
  Symlink-Schleifen, Suchbudgets, stabile IDs, atomare Persistenz, beschädigte
  Speicherdatei und veraltete Revisionen. Repo-/Index-Bytes unverändert.
- `cargo fmt --all --check`, Desktop-Typecheck und `git diff --check` grün.
- `node scripts/test_workspace_ui.mjs`: Erkennung, Gruppierung, Umbenennung,
  Neuladen/Rescan, Auflösen, explizites Worktree-Ziel, Konflikte, Teilresultate,
  Fehler, bisheriger Einzelprojekt-Einstieg und Hell-/Dunkel-Kontrast grün.
  Bestehende UI-Suites für Spec-Navigation, Farben, Aktionsausgabe, Workflow und
  Git ebenfalls grün. Browser-Checks verwenden isolierte Mock-Daten.
- Website-Pflege nach Skill `app-screenshots`: acht bestehende Motive erneut
  aufgenommen. Ein erster MCP-Capture hatte minimale Rasterabweichungen; der
  Wiederholungslauf entspricht vollständig dem bisherigen Bildbestand.
  Keine Motive betroffen. Marketing-Build (93 Seiten), responsive Landingpage-
  und Features-Tests einschließlich 320 px und Ansicht ohne JavaScript grün.
- Native Mac-App: Wegwerf-Fixture mit `node scripts/create_workspace_fixture.mjs`
  erstellt. Zwei Repos und drei Worktrees erkannt, als Customer Portal gruppiert;
  reale lokale Speicherdatei enthält getrennte Repo-/Projekt-/Worktree-IDs.
  `api-search` über expliziten Button in eigenem Projektfenster geöffnet;
  dessen Git-Arbeitsbaum unverändert. Kein bestehendes Terminal umgelenkt.
- Nach regulärem Neustart Customer Portal mit zwei Repos wiedergefunden;
  Rescan und anschließendes Entgruppieren nativ ausgeführt. Persistierte Repo- und
  Worktree-IDs identisch; ursprüngliche Projekt-ID beim Entgruppieren wieder
  verwendet. Alle drei Demo-Arbeitsbäume laut `git status --porcelain=v1` sauber.
  Vier ursprüngliche Fenster plus Test-Worktree wiederhergestellt. Native
  Sichtprüfung einschließlich schmaler Ansicht neben Terminal; Textbereich
  erhält Mindestbreite, damit der Öffnen-Knopf darunter umbrechen kann.
- Lokaler unsignierter App-Build mit `./scripts/dev.sh --app --prepared
  --ui-port=18768`. Wiederanlauf der bisherigen vier Fenster beim ersten Update
  geprüft. Dashboard-Terminal meldet bei bestehendem Claude-Resume
  „No conversation found to continue“: offener Sitzungsbefund aus 009, keine
  Zusage nahtloser Terminal-Fortsetzung. Keine Änderung fremder Shell-Settings.
- Grenzen: Windows nicht nativ geprüft; kein aggregiertes Board, kein Team-Sync,
  keine automatische Verlagerung bestehender `.agent`-Inhalte. Menschliche
  Produktabnahme bleibt offen.

## Questions

- Speicherformat und Detaildarstellung sind technische Entwurfsarbeit; bei
  Auswirkungen auf bereits vorhandene Projektdateien Migration vorher separat entscheiden.
