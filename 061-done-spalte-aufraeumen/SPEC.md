---
station: Doing
order: 61
created: 2026-09-19
needs_human: true
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

## Tasks

- [ ] Rust: `done_at` je Spec aus History/mtime/created im Board-Eintrag.
- [ ] Projekt-Board: Fenster aus Settings, Menü in der Done-Überschrift, „Älter (N)“.
- [ ] Workspace-Board: gleiche Auswahl über die Workspace-Root-Settings.
- [ ] Tests (Rust `done_at`, Browser-Regression Board), Playbooks, Fixture.

## Verification

## Questions

Keine.
