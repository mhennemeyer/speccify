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
nach Projekt/Repo/Worktree gegliedert; ein gemeinsamer Agent im Parent-Ordner.
Bestehende Editor-/Git-/Spec-
Verträge wiederverwenden. Projektwechsel erhält Entwürfe, Ausgaben und gestartete
Workspace-Sitzung; keine stille Änderung ihrer Zielwurzel. Einzelprojektfenster bleiben.

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
- Editor- und Commit-Entwürfe überleben Projekt-/Bereichswechsel. Git und Aktionen
  erreichen ausschließlich das angezeigte Zielprojekt; Terminal-Übergaben nennen ihr Repo.
- Genau eine Workspace-Sitzung startet im Parent-Ordner und erhält die Struktur
  aller Repos mit ihren Anweisungseinstiegen. Projektwechsel und Docking starten
  keinen weiteren Agenten und ändern nicht dessen cwd. Host-Berechtigungen bleiben gültig.
- Gestartete Sitzung/Aktionen behalten ihr Ziel beim Wechsel; Öffnen des
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
- D10, 2026-09-11: Nutzer verlangt einen gemeinsamen Agenten im Parent-Ordner.
  Ersetzt die Terminal-Anteile von D3/D5: eine native Reservierung pro Workspace,
  gemeinsames Kommando und PTY unabhängig von Projektwahl. Strukturkontext mit
  kanonischen Pfaden, Gruppen und Anweisungseinstiegen wird temporär übergeben;
  keine Parent-/Kind-Anweisungsdateien anlegen oder überschreiben. Plain-Presets
  Claude/Codex automatisch, freie Kommandos unverändert mit explizitem Fallback.
  Host-Trust/Sandbox bleibt; kein automatisches Resume oder MCP-/Skill-Merging.
  Git-/Skill-Übergaben müssen ihr Repo ausdrücklich adressieren.
- D11, 2026-09-11: Abschlussprüfung findet zwei Lebenszyklusfehler: temporäre
  Kontextdatei überlebt reguläres App-Quit ohne expliziten Exit-Cleanup; ein
  synchroner Board-KPI-Scan blockiert native Fenster und Quit. Terminal-Cleanup
  an Fensterende und App-Exit binden (auch gegen verspätete Starts), KPI-Lesen
  wie Board-Lesen in spawn_blocking verlagern; kein geändertes Statistikmodell.
- D12, 2026-09-11: Nach Prozessende meldet dev.sh weiter „App läuft“: tccd hält
  nur lesende Handles auf das Binary, lsof liefert mit txt-Filter sogar Exit 0
  ohne PID. Startprüfung verwendet nun ausschließlich nichtleere PID-Treffer
  ausführbarer Mappings. Keine macOS-Prüfdienste beenden oder Rechte ändern.

## Tasks

- [x] (added) Gemeinsame Parent-Sitzung und native Ein-Instanz-Sperre implementieren.
- [x] (added) Strukturkontext automatisch für Presets, explizit für freie Hosts übergeben.
- [x] (added) Projektbezogene Terminal-Übergaben, Regressionen, Playbooks und App aktualisieren.
- [x] (added) Fenster-/Quit-Cleanup und nachgewiesene blockierende Start-Lesewege absichern.
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

### Verification · gemeinsamer Parent-Agent 2026-09-11

- Skills spec-next/speccify: iteration 1, ok; bestehende native Workspace-Verträge
  wiederverwendet, keine gefundene Library-Erweiterung nötig. OpenAI Docs für
  unterstützten Codex-Startparameter verwendet; offizielle Codex-/Claude-Referenzen
  im Workspace-Vertrag verlinkt. Freie/resumierende Kommandos bewusst nicht umgebaut.
- Native Tests: 89 bestanden, 3 ignoriert. Neue Fälle für drei echte temporäre
  Repos, unveränderte Anweisungsdateien, fehlende Wurzeln ohne Ersatz, gequotete
  Preset-Übergabe, unveränderte freie Kommandos und Ein-Instanz-Reservierung.
- Neun Browser-Suites grün. Workspace-Fälle belegen gemeinsames Kommando,
  Kontextvorschau, genau eine Parent-PTY-Anforderung, erhaltene Sitzung bei Wechsel/
  Umgruppieren/Docken und explizites Zielrepo im Commit-Auftrag. Fehlendes Kind
  sperrt seine Projektaktionen, nicht die gemeinsame Sitzung. Typecheck grün.
- Skill app-screenshots: acht Motive vollständig visuell geprüft und bytegleich;
  Marketing-Build (93 Seiten), Desktop-/Mobilbreiten und Links ohne JS grün.
- Native App PID 74722: itsdcloud mit drei Repos und 66 Specs wiederhergestellt.
  Shell PID 77245 gestartet: lsof-cwd und Terminal-pwd bestätigen den Parent-Ordner.
  SPECCIFY_WORKSPACE_ROOT identisch, SPECCIFY_WORKSPACE_CONTEXT zeigt private
  temporäre Datei mit app/infra/portal, verfügbaren Pfaden und Anweisungseinstiegen.
  Auswahl infra erhält exakt PID 77245 und Parent-cwd. Keine Repo-Testmutationen.
- Beobachtung: Login-Shell meldet vorhandenen Verweis auf fehlende ~/.cargo/env;
  Workspace-Start funktioniert trotzdem. Keine Benutzer-Shellprofile verändert.
  Fenster waren zunächst nicht per Accessibility erreichbar, später vollständig
  geladen. End-to-end-Aufgabe mit angemeldetem Claude/Codex und Windows bleibt
  menschliche Praxisabnahme; Startkontext ist keine Garantie für Host-Verständnis,
  alle MCP-Konfigurationen oder zusätzliche Schreibrechte.
- Exit-Gegenprobe fand eine liegengebliebene private Kontextdatei trotz beendetem
  Shell-Prozess. Testdatei entfernt; expliziter RunEvent::Exit-Cleanup und
  Fenster-Destroy-Cleanup ergänzt. PTY-Test belegt geleerte Sessions/Reservierungen
  und gelöschte Kontextdatei; Startup verwirft verspätete Ergebnisse nach Quit.
- Sample von PID 86996 belegt erneut project_board_kpis → spec_dirs → read_dir →
  open auf dem Hauptthread; reguläres Quit hing ebenfalls. Keine Kindprozesse,
  gezielt per SIGTERM beendet. KPI-Command jetzt asynchron, unveränderte Berechnung
  über spawn_blocking; bestehender Roundtrip-Test prüft den neuen async-Einstieg.
  Gesamtsuite nach beiden Korrekturen: 89 bestanden, 3 ignoriert.
- Startskript: rein lesender tccd-Dateizugriff und lsof-Erfolg ohne Ausgabe
  werden nicht mehr als laufende App behandelt. Vorhandene Portbesitzer-Prüfung
  bleibt bestehen; neun isolierte Startskript-Tests grün. Anschließender Build
  startet trotz weiterhin vorhandener Lesehandles des unveränderten Systemdienstes.
- Zweiter Sample (PID 2448) zeigt denselben Hauptthread-Block im Dateibaum
  project_tree → list_dir → read_dir. Auch dieser Command liest jetzt in
  spawn_blocking; bestehender Dateibaum-Test prüft den async-Einstieg. Blockierten
  Prozess nach erfolglosem Quit und Prüfung auf fehlende Kindprozesse gezielt per
  SIGTERM beendet, keine Systemdienste verändert. Rust-Gesamtsuite erneut grün.
- Dritter Sample (PID 11432) lokalisiert einen weiteren Startblock im synchronen
  Git-Status mit 30-Sekunden-Timeout. Die drei initialen lesenden Git-Abfragen
  Status/Log/Branches laufen jetzt ebenfalls in spawn_blocking; Mutationen und
  Timeout-Vertrag unverändert. Reale Git-Roundtrips prüfen die async-Einstiege.
- Weitere native Gegenprobe (PID 20129): wiederhergestelltes Dokument blockiert
  in project_read_file → read_to_string → open. Auch Dokument-Lesen läuft nun
  im Hintergrund. Erfolgsfall und Traversal-Abweisung durch die bestehende
  Testsuite am async-Einstieg geprüft; Schreib- und Pfadverträge unverändert.
- Finaler nativer Build PID 28714: sechs Fenster wiederhergestellt und bedienbar.
  Sichtbarer Parent-Terminal startet Shell PID 30397 in itsdcloud; Kontextdatei
  vorhanden. Reguläres Quit beendet beide Prozesse und entfernt die Datei:
  native Exit-Gegenprobe jetzt grün. Danach mit dev.sh --open wieder geöffnet;
  finale App PID 31067 auf 18768, dieselben sechs Fenster nativ bestätigt.
  App bleibt ohne Dev-Watcher offen; UI-Testserver beendet. Keine Publikation.
  Git-Diff-/Format-/Typecheck-/Startskript-Prüfungen grün. Menschliche Abnahme offen.

## Questions

Keine offenen Fragen.
