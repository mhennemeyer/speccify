---
station: Backlog
order: 9
created: 2026-09-10
needs_human: true
ready: false
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

## Tasks

- [ ] Bestehende Git-Aktionen und Entwurfs-/Fehlerpfade inventarisieren.
- [ ] Git-Layout mit sichtbarem Commit-Composer und Branch-Einstieg umsetzen.
- [ ] Branch-Verwaltungsvertrag ergänzen und sichere native Operationen implementieren.
- [ ] Commit-/Branch-Flows mit schmutzigem Working Tree und Fehlern prüfen.
- [ ] UI-Baum, Betriebsstand und Abnahme aktualisieren.

## Verification

Findings gegen den aktuellen UI-Code geprüft; Planung, noch keine Umsetzung/Abnahme.

## Questions

Keine blockierende Produktentscheidung für diesen Schnitt.
