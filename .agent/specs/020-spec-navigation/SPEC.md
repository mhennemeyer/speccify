---
station: Doing
order: 8
created: 2026-09-10
needs_human: true
ready: true
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
- D5, 2026-09-10: Fortsetzungsauftrag startet 020. Gesamtliste und Board enthalten
  Altbestand ohne Verschieben; dessen gespeicherte Station bleibt sichtbar,
  unbekannte Alt-Stationen sind über die Liste lesbar, nicht still umgedeutet.
- D6: Auswahl und Historie werden durch den relativen Spec-Dateipfad adressiert,
  damit gleichnamige aktive/historische IDs keine falschen Details liefern.
  Altbestand bleibt in Spec-Aktionen schreibgeschützt; allgemeiner Dateieditor
  und externe Werkzeuge sind keine systemweite Schreibsperre.
- D7: Projektsortierung bleibt ausdrücklich Folgestufe nach 015/016; Abnahme
  dieses Schnitts betrifft das aktuelle Einzelprojekt mit Altbestand.
- D8: CI des Zwischenstands b5764e1 zeigt drei konkrete Plattformfehler:
  Linux-Testimage ohne zsh, CRLF-Checkout der Spec-Vorlage auf Windows und
  Windows-Separatoren im Skill-Quellennamen. Als Prüfkorrektur hier ergänzt;
  kein Abschalten der betroffenen Tests, kein breites Dependency-Upgrade.

## Tasks

- [x] Altbestand und Archiv-Abhängigkeiten in UI, Backend, Policy und Tests inventarisieren.
- [x] Gesamtliste mit Suche, Auswahl und konsistenter Board-/Inspektor-Navigation bauen.
- [x] Archiv-Bedienweg entfernen und Altbestand verlustfrei auffindbar halten.
- [x] Workflow-Vorlagen mit sicherer Versionsmigration aktualisieren.
- [x] Regression und lokalen UI-Durchlauf prüfen, menschliche Abnahme vorbereiten;
  Projektsortierung als Folgeschnitt nach 015/016 festhalten.

## Verification

- Gemeinsame Gesamtliste/Board-Filter und pfadbasierte Auswahl im Browser geprüft;
  unbekannte historische Stationen bleiben als zusätzliche Lesespalten sichtbar.
  Archivieren-Command aus der Tauri-Registrierung und Implementierung entfernt.
  Spec-Aktionen verweigern Schreiben in Altbestand; Nummerierung verändert dessen
  Parent-Verweise nicht. Allgemeiner Dateieditor ist davon nicht gesperrt.
- Neuer nativer Test deckt gleiche IDs in aktivem/historischem Ordner mit getrennter
  History ab, plus falsche Id/Pfad, Antworten, Task-Klick, Move, Save, Delete und
  Nummerierung. Alt-Datei und Historie bleiben bytegleich. Done bleibt am selben Ort.
- Policy v5: unveränderte bekannte Vorlagen 1–4 migrieren sicher; zweimaliges Setup,
  angepasste und unbekannte Versionen bleiben getestet. Explizite Nur-Lese-Diagnose
  mit `SPECCIFY_CHECK_PROJECT` meldet für dieses Repo `current`, v5, keine Befunde.
- `cargo test --workspace`: 107 bestanden, 2 ignoriert; Format und Typecheck grün.
  CRLF-Template-Regressionsfall und Windows-Quellennamen zusätzlich lokal geprüft.
- Vier Playwright/Chrome-Suiten gegen isoliertes Vite-Mock auf 1421 grün:
  `test_spec_navigation.mjs`, `test_workflow_ui.mjs`, `test_ui_colors.mjs`,
  `test_action_output.mjs`. Navigation prüft Altbestand, Tastatur, Suche/Reset,
  Themenfilter, Watcher, gleiche IDs mit passender History, leere Liste und
  ausgeblendete Panels. Visuelle Gegenprobe der Browseransichten bestanden.
- `pnpm --filter speccify-marketing build`: 92 Seiten erfolgreich gebaut.
  Integrierte Hilfe und aktuelle Website-Einstiege auf Abschluss ohne Archivieren
  angepasst. Historische Tutorial-Texte bleiben Gegenstand der geplanten Neufassung.
- Zwischenstand b5764e1 auf origin/main gesichert; Website/Deploy grün. CI meldete
  die drei unter D8 erfassten Plattformfehler; erneute Remote-Prüfung nach Push offen.
  Die vollständige Python-Suite und Ruff waren vor dem Zwischen-Commit grün;
  danach keine Python-Änderung. Sandbox-Portfehler durch freigegebene Testläufe geklärt.
- Lokale App aktualisiert: Debug-Build erfolgreich, aktuelle Binärdatei per `cmp`
  bestätigt; PID 80479 auf 18768, Hauptfenster und Projekte speccify/AVC wieder offen.
  Gezielter nativer Screenshot zeigt 54/54 Specs links und keinen Archiv-Bedienweg;
  Altbestand erscheint in Done mit Leseschutz-Hinweis. Live-HTTP-Smoke grün.
  Testserver danach beendet. Beim ersten Buildversuch war der alte Quit noch
  nicht abgeschlossen; nach bestätigtem Prozessende regulär neu gebaut.
- Terminal meldet weiterhin eine parallel geöffnete Conversation. Keine
  automatische Übernahme; exakte Session-Fortsetzung bleibt in Spec 009 offen.
  Implementierung bereit zur menschlichen Abnahme, Doing/ready=true.

## Questions

Keine blockierende Produktentscheidung für diesen Schnitt.
