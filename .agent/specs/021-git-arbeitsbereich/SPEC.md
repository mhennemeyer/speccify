---
station: Doing
order: 9
created: 2026-09-10
needs_human: true
ready: true
parent: null
---
# Git als auffindbarer IDE-Arbeitsbereich

## Why

Der Nutzer findet die Commit-Nachricht nicht und erwartet komfortable Branch-Verwaltung. Funktionen sind teilweise vorhanden, ihre versteckte Anordnung verhindert flüssiges Arbeiten.

## What

Git-Arbeitsbereich mit klarer Hierarchie: Repo/Worktree und aktueller Branch, Änderungen/Index, Diff, sichtbarer Commit-Composer und Branch-Auswahl. Bestehende native Befehle wiederverwenden. Commit-Nachricht mit Betreff und optionalem Body, Entwurfserhalt und eindeutiger Aussage, welche gestageten Dateien in den Commit gehen.

Branches suchen, wechseln, anlegen; gezielte Erweiterung um Umbenennen und sicheres Löschen lokaler Branches sowie Remote-/Tracking-Anzeige. Merge/Rebase, Konflikteditor und PR-Integration sind weitere Schnitte, nicht Teil des ersten Layoutumbaus.

## Acceptance

- Ohne Dokumentation ist der Commit-Composer aus Git direkt erreichbar, auch bei ausgeblendetem Inspektor; Nachricht bleibt bei Datei-/Diff-Wechsel erhalten.
- Leere Nachricht/fehlende gestagete Änderungen verhindern Commit mit verständlicher Erklärung. Normales Commit umfasst nur den sichtbaren Index; kein verstecktes Alles-stagen oder Push.
- Branch-Wechsel zeigt Repo, aktuellen und Zielbranch. Bei gefährdeten lokalen Änderungen wird abgebrochen oder eine explizite Entscheidung verlangt, niemals automatisch verworfen/gestasht.
- Lokale Branches lassen sich suchen, anlegen, wechseln und umbenennen; aktueller bzw. nicht integrierter Branch wird nicht unbemerkt gelöscht. Force-Delete gehört nicht zum Standard.
- Laufstatus, Erfolg und Fehler von Git-Aktionen bleiben sichtbar; kein Doppelstart und keine irreführende Erfolgsmeldung.
- Zwei Wegwerf-Repos mit unstaged/staged/untracked Änderungen, Mehrzeilen-Nachricht und Switch-Konflikt: keine Änderung im falschen Repo.

## Decisions

- D1, 2026-09-10: Bestand: Git → Commit… öffnet Inspektor mit Nachrichtenfeld; dort auch Branches-Tab mit Wechsel/Anlegen. Problem ist Auffindbarkeit, nicht ausschließlich fehlende Backend-Funktion.
- D2: Farbe folgt 019/UI-Playbook. Git-Diff grün/rot beschreibt hinzugefügt/entfernt; Projektfarbe ist kein Git-Status.
- D3: Keine echten Projekt-Commits oder Branch-Wechsel für UI-Tests; temporäre Repositories verwenden.
- D4, 2026-09-10: Composer bleibt im Hauptbereich sichtbar, unabhängig von Navigator und Inspektor. Projektgebundener Entwurf wird synchron lokal gespeichert. „Alles committen“ entfällt; Stagen und Commit bleiben getrennte Schritte.
- D5, 2026-09-10: Branch-Verwaltung zeigt lokale und Remote-Refs; Remote-Refs sind zunächst nur lesbar. Wechsel bestätigt Quelle/Ziel, Git schützt gefährdete Änderungen ohne Stash/Force. Löschen erfordert Bestätigung und Integration in den aktuellen HEAD; aktueller Branch und belegte Worktrees bleiben geschützt.
- D6, 2026-09-10: Vorherige Version 93412b6: CI, Docs und Deployment erfolgreich. Keine offenen CI-Regressionen vor Beginn.

## Tasks

- [x] Bestehende Git-Aktionen und Entwurfs-/Fehlerpfade inventarisieren.
  - Commit-Entwurf bisher nur React-State; Tastatur/Toolbar konnten Aktionen doppelt starten. Branch-Namen bisher nicht vor Options-/Revisionssyntax geschützt.
- [x] Git-Layout mit sichtbarem Commit-Composer und Branch-Einstieg umsetzen.
- [x] Branch-Verwaltungsvertrag ergänzen und sichere native Operationen implementieren.
- [x] Commit-/Branch-Flows mit schmutzigem Working Tree und Fehlern prüfen.
- [x] UI-Baum, Betriebsstand und Abnahme aktualisieren.

## Verification

- `cargo test --workspace`: 108 bestanden, 2 bestehende explizit ignorierte Tests.
- Git-Integrationstest mit zwei Wegwerf-Repositories: Index/Arbeitsbaum getrennt,
  Mehrzeilen-Commit, Fehler ohne Index/Betreff, Switch-Konflikt ohne Datenverlust
  oder Stash; Name-/Revisionsvalidierung, Umbenennen ohne Überschreiben,
  aktueller/nicht integrierter/belegter Branch geschützt; zweites Repo unverändert.
- `scripts/test_git_workspace.mjs`: sichtbarer Composer auch ohne Seitenleisten,
  Reload-/Projekt-Entwürfe, Mehrzeilen-Nachricht, kein implizites Stagen,
  Doppelstartschutz, persistente Fehler, Suche und bestätigte lokale Branch-Aktionen,
  Remote-Refs ohne Mutationsknöpfe. Hell-/Dunkel-Kontrast am echten Branch-Knopf geprüft.
- Bisherige vier UI-Suiten (`test_spec_navigation`, `test_ui_colors`,
  `test_action_output`, `test_workflow_ui`) grün; Typecheck, Rust-Format und Diff-Check grün.
- Remote-Ausgabe zusätzlich geprüft: verzögerte Listener, sofortige erste Ausgabe,
  Doppelstartschutz auch über Toolbar, fremde Exit-Events ignoriert, Start bei
  Listener-Fehler verhindert, Exit-Fehler sichtbar.
- Lokales Debug-Bundle gebaut und am 2026-09-10 neu gestartet: PID 18058 auf 18768,
  Binary/Bundle identisch, Hauptfenster und speccify/AVC wiederhergestellt.
  Live-HTTP-Handshake und zehn negative Boundary-Prüfungen bestanden.
- Neustart nicht nahtlos: Fenster zunächst mehrere Minuten leer; Stack-Snapshot
  zeigt synchrones `project_workflow_status → policy_state → fs::read_to_string → open`
  auf dem UI-Thread. Anschließend Oberfläche/Terminals wieder sichtbar, ohne
  Force-Kill oder Berechtigungsumgehung. Ursache des blockierten Dateizugriffs
  nicht abschließend bewiesen; als Betriebsrisiko im Stand-Playbook festgehalten.
- Native Sichtprüfung 19:42 UTC: Board geladen (54/54), Terminal sichtbar;
  bestehender Conversation-Übernahmekonflikt weiterhin offen. Git-Klickpfade in
  isoliertem Browser geprüft; echte menschliche Alltagsabnahme steht aus.

## Questions

Keine blockierende Produktentscheidung für diesen Schnitt.
