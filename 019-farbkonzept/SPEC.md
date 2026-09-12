---
station: Doing
order: 0
created: 2026-09-10
needs_human: true
ready: true
parent: null
---
# Farbkonzept v1: Orientierung im Projektfenster

## Why

Die Oberfläche wirkt zu grau. Farbe soll Bereiche, Zustand und Dateitypen schneller erkennbar machen, ohne Lesbarkeit und Arbeitsruhe zu verlieren.

## What

Erster direkt beauftragter Schnitt: zentrale semantische Farbpaare für Hell/Dunkel, farbige Bereichsnavigation, Board-Spalten und Auswahl, Fortschritt sowie Dateityp-Symbole. Das stehende Konzept liegt im [UI-Playbook](../../playbooks/ui-gestaltung.md). Kein umfassender Redesign, keine Theme-Engine, keine Änderungen an Git- oder Dateischreibverträgen.

## Acceptance

- Bereiche und Status sind farblich unterscheidbar, bleiben aber durch Namen, Symbole und Auswahlmarkierungen ohne Farbe verständlich.
- Hell/Dunkel behalten lesbare Akzenttexte; neue Text-/Flächenpaare erreichen im automatisierten Kontrastcheck mindestens 4,5:1.
- Dateibaum zeigt unterschiedliche Formen für Quelltext, Konfiguration, Dokumente, Bilder und Ordner; Unbekanntes erhält neutrales Dateisymbol.
- Auswahl, Theme-Wechsel, Task-Konfliktbehandlung und Ausgabetabs funktionieren weiterhin.

## Decisions

- D1, 2026-09-10: Nutzer beauftragt sofortigen ersten Farbschnitt mit anschließender Verfeinerung. Größere Interaktionsänderungen separat in 020–022.
- D2: Bestehende SVG-/CSS-Mittel verwenden; keine Icon-Bibliothek oder Bildassets nötig.
- D3: Dateityp-Farben sind Dateinamen-Hinweise, keine Behauptung vorhandener Sprachdienste. Projektzugehörigkeit später als eigenes beschriftetes Badge, nicht über Statusfarben.

## Tasks

- [x] Konzept mit Rollen, Hell/Dunkel und weiteren Iterationen festhalten.
- [x] Semantische Tokens, Bereichsnavigation, Board und Dateisymbole umsetzen.
- [x] Typecheck, Kontraste, UI-Regressionsprüfung und visuelle Prüfung durchführen.
- [x] Lokale App aktualisieren, Betriebsstand und menschliche Abnahme festhalten.

## Verification

- `pnpm --filter speccify-desktop typecheck` und `git diff --check`: bestanden.
- `scripts/test_ui_colors.mjs` mit Playwright/Chrome gegen isoliertes Vite-Mock:
  beide Themes, sieben semantische Text-/Flächenpaare ≥4,5:1 und Icons auf
  Grund-/Auswahlfläche ≥3:1; Bereichswechsel, Board-Auswahl, sechs Symbolklassen,
  Dateiauswahl und Tastatur-Fokus bestanden. Namensklassifizierung inklusive
  Großschreibung, Windows-Pfad und .env.local geprüft.
- `scripts/test_workflow_ui.mjs`: Setup- und Task-Konfliktabläufe weiterhin grün.
- `scripts/test_action_output.mjs`: beide Dock-Layouts mit Start/Stop/Fehler,
  Output-Limit, parallelen Aktionen und Listener-Fehler weiterhin grün.
- Board und Dateibaum im isolierten Browser für Hell/Dunkel visuell geprüft.
  Neue Akzente sind erkennbar, Texte unverändert lesbar. Vorhandene fest helle
  Frage-Badges/-Panels und weitere Bedienelemente bleiben spätere Vereinheitlichung;
  kein Anspruch auf vollständige Barrierefreiheit des gesamten Bestands.
- Keine nativen Schreibverträge verändert; keine erneute vollständige Rust- oder
  Python-Suite für diesen Frontend-/Dokumentationsschnitt.
- `bash scripts/dev.sh --app --prepared --ui-port=18768`: Debug-Bundle erfolgreich,
  bekannte Vite-Chunkgrößenwarnung; `cmp` bestätigt aktuelle gebündelte Binärdatei.
  App PID 54016 läuft ohne Watcher auf 18768. Live-HTTP-Smoke (Handshake und zehn
  negative Grenzfälle) bestanden; Testserver 1421 anschließend beendet.
- Native Fensterliste und gezielter Screenshot am 2026-09-10 18:14 UTC:
  Hauptfenster sowie speccify/AVC-Projektfenster wieder da, passend zu den zwei
  aktuell gespeicherten Pfaden. Farbige Navigation/Board im echten Projekt sichtbar;
  kein offener System-Zugriffsdialog in diesem Fenster. iKanban steht inzwischen
  nicht mehr in der gespeicherten Liste, daher nicht zusätzlich geöffnet.
- Agent-Terminal wieder da, zeigt jedoch „This conversation is open in another
  app“. Keine automatische Übernahme einer parallelen Sitzung. Nahtlose Fortsetzung
  damit nicht belegt; bestehendes Sitzungsproblem gehört zu Spec 009.

Implementierung zur menschlichen Stil-/Alltagsabnahme: Doing, ready=true.

### Speccify · iteration 1 · ok

- Bibliothekssuche via Workspace-CLI nach `color` und `design`: keine Treffer.
  Keine Bibliothek installiert/expandiert; vorhandene CSS-/SVG-Mittel genutzt.
- Gegenprobe: dunkle/helle Kontrastpaare, farbunabhängige Formen/Labels,
  Auswahl/Fokus und bestehende UI-Flows. Alle automatisierten Prüfungen grün;
  menschliche Stil-/Alltagsabnahme bleibt offen.

## Questions

Keine blockierende Produktentscheidung für diesen Schnitt.
