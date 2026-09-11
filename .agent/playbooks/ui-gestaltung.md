---
description: Lebendes Farb- und Interaktionskonzept für den IDE-Arbeitsbereich
---
# UI-Gestaltung: Farbe mit Bedeutung

Stand 2026-09-10. Erste Iteration in [019](../specs/019-farbkonzept/SPEC.md),
weitere Findings in [020](../specs/020-spec-navigation/SPEC.md),
[021](../specs/021-git-arbeitsbereich/SPEC.md),
[022](../specs/022-dateiauswahl-und-refactoring/SPEC.md).
Produktvision: [Weiterentwicklung](weiterentwicklung.md); tatsächlich gelieferte
Ansichten und Prüfgrenzen: [Stand und UI](stand-und-ui.md).

## Richtung

**Verbindliche Präzisierung 2026-09-11 (026):** Mehrprojekte erweitern das
Einzelprojektfenster, sie erhalten keine eigene Bedienoberfläche. Dieselbe kompakte
Toolbar, zweistufige Bereichsnavigation, Splitter, Inspektor-/Ausgabetabs und
Terminal-Docks verwenden. Projektgruppen innerhalb der Listen ergänzen, gemeinsam
überblickbares Board erhalten. Gemeinsame Komponenten statt auseinanderlaufender
Nachbauten; Parität ausdrücklich testen. Titel und Pfad sind Fenster-Ziehflächen,
interaktive Toolbar-Elemente bleiben klickbar. Dieses Prinzip gilt auch für künftige
Funktionen, nicht nur als optische Nachbesserung dieses Schnitts.

Eine aufgeräumte IDE mit farbigen Orientierungspunkten. Editor, Text, Diffs
und Ausgaben behalten ruhige, überwiegend neutrale Flächen. Bereiche erhalten
farbige Icons und leicht getönte Auswahlflächen; Status kommt als zusätzliche
Beschriftung und Markierung hinzu. Kein Regenbogen auf jeder Karte, keine
großflächigen Verläufe hinter Text. Bestehende kompakte Typografie bleibt.

## Farbrollen v1

| Rolle | Akzent | Anwendung |
| --- | --- | --- |
| Navigation/aktive Arbeit | Blau | Dateien/Git-Bereich, Doing, Datei-Auswahl, Fokus |
| Planung/Wissen | Violett | Specs- und Orga-Navigation, Konfiguration |
| Werkzeuge | Petrol/Teal | Technik-Navigation, Dokument-Symbole |
| Abgeschlossen/Erfolg | Grün | Done, vollständiger Task-Fortschritt |
| Aufmerksamkeit | Amber | künftig offene Abnahme/Fragen; Ordnersymbole als Dateityp-Hinweis |
| Fehler/Destruktiv | Rot/Rose | Fehler- und Löschaktionen; Bildsymbol im getrennten Dateityp-Kontext |
| Neutral | Slate | Backlog, unbekannter Dateityp, sekundäre Bereiche |

Status-, Bereichs- und Dateitypfarbe sind getrennte Kontexte. Die Farbe eines
Ordners bedeutet keine Warnung, die eines Bildes keinen Fehler. Spätere
Projektzugehörigkeit immer mit Projektname/Badge darstellen; nicht Doing- oder
Fehlerfarben umdeuten. Git-Diff behält hinzugefügt/entfernt mit Zeichen und Farbe.

Quelle: `apps/desktop/src/index.css`. Pro Akzent drei semantische Werte:
`ink` für Text/Icon/Markierung, `soft` für Fläche, `line` für dezente Umrandung.
Eigene Hell-/Dunkelwerte statt blindem Spiegeln der Akzentpalette. Neue Bausteine
nutzen `data-tone` und gemeinsame Klassen, keine verstreuten Hexwerte in Views.

## Lesbarkeit und Bedienung

- Text auf neuen Akzentflächen mindestens 4,5:1; sichtbare Icons und Fokuslinien
  mindestens 3:1 auf ihrem Hintergrund. Prüfung beider Themes mit berechneten
  Browserfarben; keine pauschale Barrierefreiheitszertifizierung daraus ableiten.
- Farbe nie allein: Bereichsname/Tooltip und Icon, Station als Text, Auswahl
  mit Umrandung/Unterstrich, Dateitypen mit verschiedenen SVG-Formen.
- Fokus sichtbar, keine Animation nötig; reduzierte Bewegung respektieren.
- Dateinamen bleiben unverändert lesbar. Symbole sind Dateinamen-Heuristiken,
  keine Garantie für Editor-/LSP-/Refactoring-Unterstützung.
- Terminals und vorhandene Charts bleiben in v1 unverändert. Neue Statusfarben
  nicht pauschal per globalem Ersetzen auf Fremdkomponenten anwenden.

## Erste Umsetzung und nächste Verfeinerung

019 liefert Bereichstabs, Board-Spalten/Auswahl/Fortschritt und Dateisymbole.
Größere Interaktionsänderungen sind ausdrücklich noch nicht damit geliefert:

1. 020: Gesamtliste links und Such-/Themenfilter über dem Board umgesetzt;
   kein Archiv-Bedienweg, Altbestand als beschriftete schreibgeschützte Einträge.
   Unbekannte historische Stationen bleiben lesbar statt still umgedeutet.
   Später nach Projekt gruppieren/sortieren.
2. 021 umgesetzt: Git-Composer mit Betreff/Body und Index-Vorschau im Hauptbereich;
   Branch-Verwaltung mit Suche, lokalen Aktionen und separater Bestätigung.
   Blau für Branch-Einstieg, Grün für Index-Commit, Rose für Löschbestätigung.
   `tone-surface` kombiniert Akzenttext und weiche Fläche für lesbare Hell-/Dunkel-
   Zustände; `tone-fill` bleibt für reine Farbbalken. Entwürfe und Git-Sicherheit
   gehen vor Optik. Menschliche Alltagsabnahme offen.
3. 022: Dateien und Ordner auswählen, Kontextmenü, später Move/Refactoring mit
   Vorschau. Auswahl ist nicht dasselbe wie Öffnen oder Aufklappen.
4. Nach Alltagsfeedback Dichte, Abstände, Status-Badges und gemeinsame
   Bedienelemente vereinheitlichen; anschließend Charts/Leerzustände prüfen.

Dieses Dokument bei Änderungen an Rollen oder Interaktionsprinzipien anpassen.
Screenshots und Prüfergebnisse gehören zur jeweiligen Spec, nicht als unbelegte
Fertigmeldung in die Vision.
