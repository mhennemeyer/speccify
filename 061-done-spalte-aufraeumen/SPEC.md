---
station: Doing
order: 61
created: 2026-09-19
needs_human: true
ready: true
---
# Done-Spalte: nur Aktuelles offen, Älteres eingeklappt, pro Board einstellbar

## Why

BO 2026-09-19: Die Done-Spalte wächst unbegrenzt (im eigenen Repo über 60
Specs) und ist unübersichtlich. Gewünscht: nur die Karten der letzten X Tage
zeigen, den Rest eingeklappt; pro Board konfigurierbar mit vernünftigem Default.

## What

- Kriterium „Done seit“: Zeitpunkt des letzten `station_changed` nach Done aus
  `history.jsonl`; Fallback Änderungszeit der `SPEC.md`, dann `created`.
- Done zeigt Karten innerhalb des Fensters wie bisher nach Thema gruppiert;
  Älteres eingeklappt unter „Älter (N)“ am Ende, weiter klick- und durchsuchbar.
  Die Spaltenüberschrift zählt weiterhin alle.
- Fenster pro Board über ein Menü in der Done-Überschrift (7/14/30/90 Tage,
  alle); gespeichert in `.agent/settings.json` als `board.doneDays` — pro
  Projekt-Board bzw. pro Workspace-Root, versioniert, fürs Team gleich.
- Default 14 Tage. Eine Suche/ein Elternfilter zeigt weiterhin alle Treffer.
- Außerhalb: Archiv-Bestand bleibt unverändert; keine neuen Frontmatter-Felder;
  kein automatisches Verschieben oder Löschen.

## Acceptance

- Wenn eine Spec vor mehr als `doneDays` Tagen nach Done kam, dann liegt sie
  eingeklappt unter „Älter“; jüngere bleiben sichtbar gruppiert.
- Wenn das Fenster im Menü geändert wird, dann gilt es sofort, steht danach in
  `.agent/settings.json` und nach Neuladen weiterhin.
- Wenn eine Spec keine History hat, dann zählt die Dateiänderungszeit, sonst
  `created`; nichts fällt durch (jede Done-Spec ist entweder aktuell oder älter).
- Wenn ein Suchtext oder Elternfilter gesetzt ist, dann werden Treffer nicht
  durch das Fenster verborgen.

## Decisions

1. 2026-09-19: Kriterium ist „Done seit“, nicht `created`: Alte Ideen, die spät
   erledigt wurden, gehören zum Aktuellen.
2. 2026-09-19: Ablage in `.agent/settings.json` statt Browser-Speicher: „pro
   Board“ heißt pro Projekt/Workspace und für alle gleich; kein neues Modell.
3. 2026-09-19: Default 14 Tage; „alle“ stellt das bisherige Verhalten her.
4. 2026-09-19 (BO-Nachtrag): Zusätzlich höchstens N Karten auf einmal, darunter
   „Mehr anzeigen“ als Link ohne Button-Optik; N konfigurierbar. Default 10,
   Optionen 5/10/20/50/alle, `board.doneLimit`; jeder Klick holt N weitere,
   auch innerhalb von „Älter“. Zähler setzt sich bei Filter-/Suchwechsel zurück.

## Tasks

- [x] Rust: `done_at` je Spec aus History/mtime/created im Board-Eintrag.
- [x] Projekt-Board: Fenster aus Settings, Menü in der Done-Überschrift, „Älter (N)“.
- [x] Workspace-Board: gleiche Auswahl über die Workspace-Root-Settings.
- [x] Tests (Rust `done_at`, Browser-Regression Board), Playbooks, Fixture.
- [x] (added) N Karten + Link „Mehr anzeigen“, `board.doneLimit`, beide Boards, Regression, Doku.

## Verification

Rust `board_reads_specs_and_moves_byte_stable` erweitert: Done ohne History →
RFC-3339-Änderungszeit; mit History gewinnt der letzte `station_changed` mit
Done trotz späterer Ereignisse und kaputter Zeile; nicht-Done → kein `done_at`.
Desktop-Rust 134 bestanden/3 ignoriert, Cargo fmt, TypeScript, Marketing-Build
(113 Seiten) grün.

Browser `scripts/test_board_done_window.mjs` (Fixture `?donewindow`, Alter
relativ zu heute): Default 14 → 3 offen, „Älter (2)“ zu, Überschrift zählt 5,
neueste zuerst; eingeklappte Karte anklickbar; 30 → `board.doneDays: 30` im
Settings-Mock, 14 löscht den Schlüssel, 0 entfernt „Älter“; `?donedays=90`
wird beim Laden gelesen; Suche zeigt Treffer trotz Fenster; Workspace-Board hat
dieselbe Auswahl und schreibt `board.doneDays` an die Workspace-Wurzel.
Nachbarsuiten workspace_board, spec_navigation, spec_register, spec_owner,
team_signals grün. `test_workspace_ui` schlägt unabhängig davon auch auf dem
unveränderten Stand fehl (Discovery-Tiefen-Text „Nicht durchsucht“) — nicht
Teil dieser Spec, separat ansehen.

Screenshot des Mock-Boards (1400×800) gesichtet: Auswahl „Letzte 14 Tage“
in der Done-Überschrift, Gruppen, ältere Karten unten eingeklappt.
Nicht nachgewiesen: Sichtprüfung in der gebauten App (braucht neuen Build);
Verhalten mit echtem Register-Sync der `.agent/settings.json` im Team.

## Questions

Keine.
