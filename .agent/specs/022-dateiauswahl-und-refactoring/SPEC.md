---
station: Backlog
order: 10
created: 2026-09-10
needs_human: true
ready: false
parent: null
---
# Dateien: Ordnerauswahl, Kontextmenü und sichere Refactorings

## Why

Ordner können derzeit nur auf-/zugeklappt werden. Für Aktionen wie Move müssen Dateien und Ordner gezielt auswählbar sein und ein Kontextmenü anbieten.

## What

Erster Schnitt: Auswahlzustand vom geöffneten Editor und aufgeklappten Ordner trennen; Dateien und Ordner per Klick/Tastatur auswählen, Metadaten und Aktionen am richtigen Ziel anbieten. Kontextmenü per Rechtsklick und Tastatur; bestehende Aktionen nur dort anbieten, wo sicher unterstützt. Dateityp-Symbole/Farben aus 019 weiterverwenden.

Spätere Stufe: Move/Rename mit Zielauswahl, Vorschau und Kollisionsprüfung, Mehrfachauswahl bei abgestimmtem Vertrag. Physisches Verschieben ist nicht automatisch semantisches Refactoring; Import-/Referenzanpassung benötigt Sprachdienst oder explizite Vorschau. Bis dahin keine solche Vollständigkeit behaupten.

## Acceptance

- Ein Ordner ist auswählbar, ohne eine Datei zu öffnen; Auf-/Zuklappen und Auswahl sind getrennte Bedienhandlungen. Offene Entwürfe bleiben erhalten.
- Rechtsklick auf nicht ausgewählten Eintrag setzt ein eindeutiges Aktionsziel; Kontextmenü ist per Tastatur erreichbar, Escape schließt und stellt Fokus wieder her.
- Angebotene Aktionen passen zu Datei/Ordner, Rechten und Mehrfachauswahl; unsupported/destruktive Aktionen sind erklärt bzw. abgesichert.
- Dateisymbole unterscheiden Typen auch ohne Farbe; ausgewählte Zeilen bleiben in Hell/Dunkel lesbar.
- Späterer Move: Überschreiben, Verschieben in eigene Unterordner, Root-/Symlink-Flucht und unklare Cross-Repo-Ziele werden verhindert; ungespeicherte Entwürfe werden nicht verloren.
- Ein späterer Refactoring-Plan zeigt alle Änderungen/Referenzen vor Freigabe und meldet nicht unterstützte Sprachen, statt nur einen Dateiumzug als vollständiges Refactoring auszugeben.

## Decisions

- D1, 2026-09-10: Nutzer nennt explizit Dateien UND Ordner als auswählbare Aktionsziele.
- D2: Die erste Farb-Runde 019 liefert nur Symbole/Farben, nicht Ordnerauswahl oder Kontextmenü.
- D3: Dateioperationen und semantische Refactorings getrennt spezifizieren; keine unbemerkte repoübergreifende Verschiebung.

## Tasks

- [ ] Auswahl-/Editor-/Expansion-Zustände und Tastaturbedienung entwerfen.
- [ ] Ordnerauswahl und kontextbezogenen Inspektor implementieren.
- [ ] Kontextmenü auf bestehenden sicheren Aktionen aufbauen.
- [ ] Entwurfs-, Pfad-, Fokus- und Fehlerregression prüfen.
- [ ] Späteren Move-/Refactoring-Vertrag mit Vorschau, Kollisionen und Sprachumfang konkretisieren.

## Verification

Findings gegen den aktuellen UI-Code geprüft; Planung, noch keine Umsetzung/Abnahme.

## Questions

Keine blockierende Produktentscheidung für diesen Schnitt.
