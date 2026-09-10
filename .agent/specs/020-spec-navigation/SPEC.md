---
station: Backlog
order: 8
created: 2026-09-10
needs_human: true
ready: false
parent: null
---
# Specs: linke Gesamtliste und Workflow ohne Archiv

## Why

Archiv ist laut Nutzerfindung ein Rest des alten Workflows. Links fehlen die einzelnen Specs; das Board allein reicht nicht zur Navigation.

## What

Archiv als separaten Workflow-/UI-Schritt entfernen. Links eine durchsuchbare Gesamtliste mit Nummer, Titel, Station, Bereitschaft/Frage und Fortschritt; dieselbe Auswahl steuert Board und Inspektor. Done bleibt Abschlusszustand. Vorhandene Archivdaten erhalten und ohne eigenständigen Archiv-Tab auffindbar machen. Dazu UI, Workflow-Policy/-Vorlagen und historische Einstiegshilfen konsistent aktualisieren.

Spätere Stufe nach 015/016: projektübergreifende Liste und Board nach Projekt gruppieren/sortieren/filtern; expliziter Projektname und stabile Identität. Kein vorschnelles Multi-Repo-Domänenmodell im ersten Schnitt.

## Acceptance

- Specs-Ansicht enthält weder Archiv-Navigation noch Archivieren-Aktion; Done verlangt kein Verschieben einer Spec.
- Alle vorhandenen Specs inklusive Altbestand bleiben auffindbar; keine automatische Löschung, keine unkontrollierte Rückverschiebung oder ID-Kollision.
- Klick auf einen Listeneintrag öffnet dieselbe Spec wie die Boardkarte; Auswahl und Fortschritt stimmen nach Watcher-Änderung überein.
- Suche, lange Titel, leere Liste, Filter und Tastaturauswahl bleiben bedienbar; ausgeblendete Seitenleiste verhindert keine Auswahl.
- Workflow-Einweisung verlangt kein Archivieren mehr; bekannte Vorlagen migrieren kontrolliert, individuelle Inhalte bleiben erhalten.
- Später: gleichnamige Specs aus zwei Projekten sind unterscheidbar, Sortierung/Gruppierung verändert weder Identität noch Dateien.

## Decisions

- D1, 2026-09-10: Explizite Nutzerentscheidung: Archiv wird nicht weiter als Workflow-Schritt benötigt.
- D2: Entfernung der UI ist keine Löschfreigabe für .agent/specs/archive; Altbestand zunächst als lesbare Einträge derselben Gesamtliste integrieren, historische Herkunft im Detail markieren.
- D3: Vor Umsetzung den Umgang mit Altbestands-Stationen und Schreibschutz inventarisieren. Keine Massenmigration im Hintergrund.
- D4: Projektsortierung folgt Multi-Repo-Identitäten aus 015 und gemeinsamen Spec-IDs aus 016; das ist eine spätere Stufe.

## Tasks

- [ ] Altbestand und Archiv-Abhängigkeiten in UI, Backend, Policy und Tests inventarisieren.
- [ ] Gesamtliste mit Suche, Auswahl und konsistenter Board-/Inspektor-Navigation bauen.
- [ ] Archiv-Bedienweg entfernen und Altbestand verlustfrei auffindbar halten.
- [ ] Workflow-Vorlagen mit sicherer Versionsmigration aktualisieren.
- [ ] Regression und menschlichen Durchlauf prüfen; nach 015/016 Projektsortierung als Folgeschnitt konkretisieren.

## Verification

Findings gegen den aktuellen UI-Code geprüft; Planung, noch keine Umsetzung/Abnahme.

## Questions

Keine blockierende Produktentscheidung für diesen Schnitt.
