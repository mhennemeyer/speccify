---
station: Doing
order: 9
created: 2026-09-11
needs_human: true
ready: true
parent: null
---
# Ein Arbeitsfenster für alle Projekte im Workspace

## Why

itsdcloud wird als Verbund erkannt, öffnet bisher aber nur einzelne Repo-Fenster.
Der Team-Alltag benötigt einen gemeinsamen Arbeitsbereich statt Fensterwechseln.

## What

Ein explizit geöffnetes, wiederherstellbares Workspace-Fenster für beliebig viele
erkannte Projekte/Repos (innerhalb der bestehenden Suchlimits). Gemeinsames Board
mit Herkunft; Dateien, Git, Playbooks, Skills, Tools, Aktionen, MCP-Konfiguration
und Terminals nach Projekt/Repo/Worktree gegliedert. Bestehende Editor-/Git-/Spec-
Verträge wiederverwenden. Projektwechsel erhält Entwürfe, Ausgaben und gestartete
Terminals; keine stille Änderung ihrer Zielwurzel. Einzelprojektfenster bleiben.

Kein Team-Sync, kein gemeinsamer Git-Index, keine Zusammenführung von Wissensdateien,
kein automatischer Start mehrerer Agenten und keine Cross-Repo-Refactorings.

## Acceptance

- Einzelprojekt- und Workspace-Fenster verwenden dieselbe Toolbar, zweistufige
  Navigation, Splitter und Terminal-Anordnung. Mehrprojekte ergänzen die vorhandene
  Oberfläche; sie sind kein eigener UI-Modus. Fensterziehen funktioniert auch auf
  Titel und Pfad, Toolbar-Knöpfe bleiben normal bedienbar.
- Workspace öffnen zeigt drei oder mehr Repos in einem Fenster, ohne ein
  Einzelprojektfenster pro Repo zu öffnen; wiederholtes Öffnen fokussiert dasselbe.
- Fachliche Projektgruppen enthalten ihre Repos/Worktrees in jeder Navigation.
  Gleiche Dateinamen/Skills/Spec-IDs bleiben getrennt und eindeutig gekennzeichnet.
- Das Board zeigt alle Projekte gemeinsam; Aufgaben, Fragen und Spec-Bearbeitung
  verwenden genau die ausgewählte Herkunft und erscheinen anschließend im Board.
- Editor- und Commit-Entwürfe überleben Projekt-/Bereichswechsel. Git, Aktionen
  und Terminal-Eingaben erreichen ausschließlich das angezeigte Zielprojekt.
- Gestartete Terminals/Aktionen behalten ihr Ziel beim Wechsel; Öffnen des
  Workspace startet keine Agenten automatisch in allen Repos.
- Fehlende oder veränderte Pfadbindungen werden sichtbar; kein Ersatz durch eine
  ähnlich benannte Wurzel. Gruppierung und Identitäten bleiben erhalten.
- Bestehende Einzelprojekt-UI und öffentliche Screenshot-Motive bleiben intakt;
  lokale App nach Update wieder offen, native Prüfung am Demo-Verbund.

## Decisions

- D1, 2026-09-11: Expliziter Nutzerauftrag priorisiert diesen Schnitt vor 016.
  025 wird geparkt; Nutzerbild zeigt inzwischen den geladenen itsdcloud-Workspace
  ohne Warnung. Die separate Startkorrektur ist noch nativ nachzuprüfen.
- D2, 2026-09-11: Projekt-/Repo-/Worktree-IDs aus 015 bleiben maßgeblich. Neue
  Fenstershell nutzt bestehende Projektkomponenten, keine zweite Editor-/Git-Domäne.
- D3, 2026-09-11: Pro Worktree unveränderliches Ziel und eigener UI-/Prozesszustand.
  Fensterweite Kommandos müssen beim Mehrfach-Mount auf das aktive Ziel begrenzt
  werden; dessen Dateipfad bleibt jederzeit sichtbar. Gemeinsames Board ist kein
  Team-Register und erteilt keine projektübergreifende Schreibberechtigung.
- D4, 2026-09-11: Umgruppierung verschiebt nur Navigations-Portale; stabile
  Worktree-Komponenten behalten Entwürfe und Prozesse. Hintergrund-Refresh des
  Boards aktualisiert Details, wechselt aber nicht das aktive Zielprojekt.
- D5, 2026-09-11: Watcher erhalten pro Mount eine Lebenszyklus-ID, Terminals
  kollisionsfreie IDs und abbrechbare Initialisierung. Verspätetes Aufräumen darf
  keinen neu gestarteten Watcher oder PTY eines anderen Projekts beenden.
- D6, 2026-09-11: Neue Spec verwendet den vorhandenen Projekt-Dialog. Dessen
  Zustand bleibt beim Bereichswechsel erhalten; geschlossene Dialoge öffnen
  nicht durch erneutes Mounten von selbst.
- D7, 2026-09-11: Nutzer lehnt den separaten Workspace-UI-Modus ab. Vertraute
  Projektoberfläche ist verbindlich: gemeinsame Toolbar/Bereichsnavigation,
  Splitter, Terminal unten/rechts, Ausgabetabs, Hilfe, Einstellungen und Shortcuts.
  Gruppierung ergänzt Listen; dieselben Board-Farbklassen erhalten. Keine pauschale
  Zusage vollständiger Funktionsparität: gemeinsames Board hat weiterhin kein
  Cross-Repo-Drag-and-drop oder Team-Sync, Terminal-Resume bleibt ausdrücklich aus.
- D8, 2026-09-11: Ziehfehler durch nicht als Drag-Region wirksame Titel-/Pfad-
  Kinder. Gemeinsame Toolbar verwendet Tauri `deep`; interaktive Nachfahren
  bleiben ausgenommen. Gegen exakt verwendetes Tauri-Script und nativ prüfen.
- D9, 2026-09-11: Toolbar-Rückkehr legt Kollisionsrisiko gleichnamiger Aktionen
  offen. Workspace/Worktree-Namensraum für Run-/Output-/Stop-IDs; vorhandene
  Einzelprojekt-Aufrufe und Aktionsdefinitionen unverändert.

## Tasks

- [x] (added) Nutzerkorrektur: vertraute Projektoberfläche im Workspace wiederherstellen.
- [x] (added) Titelleiste einschließlich Text verschiebbar machen und nativ prüfen.
- [x] (added) Layout-/Docking-/Toolbar-Parität sowie bestehende Isolation regressionsprüfen.
- [x] Nativen Workspace-Fenstervertrag mit Öffnen/Fokus/Wiederaufnahme implementieren.
- [x] Projektweise Navigation, bestehende Arbeitsansichten und gemeinsame Spec-Sicht.
- [x] Prozess-/Ereignis-/Editor-Isolation und fehlende Zielbindungen absichern.
- [x] Mehrprojekt-Regressionen, Einzelprojekt-Regressionen und native App prüfen.
- [x] Playbooks, UI-Baum, Vertrag und Screenshot-Pflege aktualisieren.

## Verification

- Skills spec-next und speccify gelesen. `speccify search workspace`: kein Treffer.
  Bestehende native Identitäten und Projektkomponenten als Grundlage geprüft.
- `cargo test -p speccify-desktop --offline`: 86 bestanden, 3 ignoriert.
  Neue Tests für Migration/Persistenz des Fenstermerkers und gezieltes
  Watcher-Aufräumen bei mehreren Projekten/Fenstern/Lebenszyklen.
  `cargo fmt --all --check` und Desktop-Typecheck grün.
- `scripts/test_workspace_shell.mjs`: drei Repos plus Feature-Worktree,
  kollidierende Spec-IDs/Dateinamen, Task-Rückschreiben nur in die Herkunft,
  getrennte Editor-/Commit-Entwürfe, genaues Git-/Terminal-Ziel, kein Autostart,
  Prozessfortbestand bei Wechsel und Umgruppierung, fehlendes Ziel gesperrt,
  geschlossener Spec-Dialog bleibt geschlossen, schmale Hell-/Dunkelansicht grün.
- Beide bisherigen Workspace-Suites sowie `test_spec_navigation`, `test_ui_colors`,
  `test_action_output`, `test_workflow_ui`, `test_git_workspace` grün: acht UI-Suites
  insgesamt. Kein Testschreiben in itsdcloud; Mutationen verwenden Demo-Daten.
- Skill app-screenshots: acht öffentliche Motive visuell geprüft, letzter Capture
  vollständig bytegleich zum Bestand. Marketing-Build (93 Seiten) und responsive
  Landing/Features bei 1440/390/320 px sowie ohne JavaScript grün. Keine Publikation.
- Nativer itsdcloud-Workspace über Dashboard geöffnet: app/infra/portal in einem
  Fenster, gemeinsames Board mit 66 Specs (14 Backlog, 11 Doing, 41 Done).
  Native Dateinavigation zeigt alle drei Projektgruppen; Auswahl infra setzt das
  sichtbare aktive Ziel auf `/Users/mhennemeyer/WorkLocal/itsdcloud/infra`.
  Wiederholter Klick auf „Workspace öffnen“ erzeugt kein zweites Workspace-Fenster.
- Abschließender Build `./scripts/dev.sh --app --prepared --ui-port=18768`
  erfolgreich. Reguläres Beenden/Neustart erhält das Workspace-Fenster sowie die
  fünf bisherigen Fenster. Finale App PID 27136, Port 18768, ohne Dev-Watcher;
  wiederhergestellte Projektgruppen nativ kontrolliert und Fenster offen gelassen.
- Betriebsbefund: Erster Start dieses Schnitts war vorübergehend im synchronen
  `project_board_kpis → spec_dirs → read_dir → open` verzögert. App lud danach
  selbstständig; letzter Neustart bedienbar. Keine Systemdienste oder Freigaben
  verändert. Generell verzögerungsfreier Start nicht bewiesen; Windows ungetestet.
- Grenzen: Workspace-Terminals nur explizit starten; kein PTY-Resume nach Quit.
  Große Spec-Listen können weitere Projektgruppen unter den Scrollbereich schieben;
  einklappbare Gruppen sind ein möglicher UI-Feinschliff. Kein Team-Sync oder
  automatischer Umzug von Spec-/Wissensdateien.

### Verification · Nutzerkorrektur 2026-09-11

- Skills spec-next, speccify und app-screenshots; Suche `workspace` ohne Treffer.
  Gemeinsame `ProjectNavigation` aus dem vorhandenen Projektfenster extrahiert;
  dessen gerendertes Aussehen unverändert. Workspace nutzt bestehende Toolbar,
  Layoutwerte/Splitter, SettingsSheet und TerminalPanel, zusätzlich Projektgruppen.
- `test_workspace_layout.mjs` grün: DOM-/Toolbar-Höhen-/Splitter-Parität, festgelegter
  Tauri-Drag-Code für Titel/Pfad/Leerraum und ausgeschlossene Bedienelemente,
  Tastenkürzel, einklappbare Gruppen, persistierte Breite, Docking ohne PTY-Kill,
  zwei gleichnamige Tests-Aktionen mit getrennten Ausgaben und Stop-Zielen.
- Alle acht bisherigen UI-Suites erneut grün, insgesamt neun; Typecheck grün.
  Keine Rust-Domänenänderung, lokaler Tauri-Build kompiliert erfolgreich.
- Native App 48635: Titel-Ziehtest nach gemeinsamer Aktivierung und Fokusprüfung
  bewegt itsdcloud von (114,69) auf (154,89). Vorige Versuche bei inzwischen
  anderem Vordergrundprozess nicht als Produktfehler oder Freigabeproblem werten.
- Acht öffentliche Screenshot-Motive nach gemeinsamer Komponentenänderung visuell
  geprüft. Zweiter Capture vollständig bytegleich (erste MCP-Rastervarianz entfällt).
  Marketing-Build und responsive Landing/Features-Prüfung grün; keine Publikation.
- Finaler Build einschließlich Board-Farbklassen erfolgreich; PID 53572 auf
  18768. Workspace plus fünf vorherige Fenster wiederhergestellt, native Sichtprüfung
  bestätigt 66 Specs und vertrauten Fensteraufbau. App offen, UI-Testserver beendet.
  Lokale Dokumentationslinks und `git diff --check` grün. Menschliche Abnahme offen.

## Questions

Keine offenen Fragen.
