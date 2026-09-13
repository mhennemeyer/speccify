---
station: Doing
order: 17
created: 2026-09-13
needs_human: true
ready: true
open_question: null
parent: null
---
# Ad-hoc-UI für Nutzer-I/O: der Agent fragt und zeigt über HTML/Tailwind

## Why

Vieles ist auf einer Oberfläche schneller und klarer als im Terminal: ein
Ja/Nein, eine Auswahl, mehrere Häkchen, eine Liste von Fragen mit
Textantworten — oder einfach etwas zeigen (Tabelle, Fortschritt, Vorschau).
Der Agent soll solche Oberflächen ad hoc bauen oder als Skill speichern
können; HTML mit Tailwind ist dafür das passende, überall bekannte Format.
BO-Auftrag 2026-09-13; Playbook V1-06 (Ad-hoc-UIs).

## What

Der Desktop-UI-MCP (`speccify-desktop-ui`, schon mit `ask_bo`) erhält
`show_ui`: `title`, `html` (Fragment) oder `file` (absoluter Pfad, z. B. eine
in einem Skill gespeicherte UI), `mode` `ask` (wartet) oder `show` (zeigt),
`timeout_seconds`. Die App rendert das Fragment in einem sandboxed iframe
(`allow-scripts allow-forms`, kein Same-Origin) mit eingebettetem
Tailwind-Browser-Build (offline) und einer Brücke: ein `<form>`-Submit liefert
alle Felder nach Name (gleichnamige Checkboxen als Liste, Submit-Knopf mit
`name`/`value`), ein Klick auf `data-answer="…"` liefert `{answer}`,
`speccify.submit({...})` aus einem Inline-Skript beliebige Werte; die Höhe
folgt dem Inhalt. Antwort an den Agenten: `{answered: true, values}`; bei
Timeout bleibt die Karte offen und `ui_result` holt die Antwort nach.
`show` kehrt sofort zurück; Schließen meldet `{closed: true}`.

Die Karten erscheinen über dem Terminal des Projektfensters (neu: dort
gab es bisher gar keine ask_bo-Anzeige) und in der Dashboard-Seitenleiste;
eine neue Frage holt das Terminal nach vorn. Beantwortete Karten frieren ein
und zeigen die Antwort. Der Skill `agent-ui` (per *Einrichten*) erklärt beide
Tools und liefert Muster (Ja/Nein, Auswahl, Mehrfachauswahl, Fragenliste,
Anzeige); die Policy (v9) verweist darauf.

Nicht enthalten: externe Ressourcen im Frame (Sandbox, kein Netz nötig),
persistente Panels/Zeitreihen für Aktionen (V1-06 später), Antworten aus dem
Web-Board oder itsdcloud.

## Acceptance

- Wenn der Agent `show_ui` mit einem Formular ruft, dann zeigt die App das
  Fragment mit wirksamen Tailwind-Klassen; ein Submit liefert die Werte nach
  Name (Checkboxen als Liste, Knopf-Wert dabei) als Tool-Ergebnis; die Karte
  friert ein und zeigt die Antwort.
- Wenn ein Element mit `data-answer` geklickt wird, dann kommt `{answer}`
  ohne Formular an.
- Wenn `mode: show` genutzt wird, dann kehrt das Tool sofort zurück; Schließen
  liefert `{closed: true}` über `ui_result`.
- Wenn `file` auf eine gespeicherte UI zeigt, dann wird sie gelesen; relative
  Pfade, fehlende Dateien und mehr als 512 KB werden abgelehnt.
- Wenn die Frage im Projektfenster gestellt wird, dann erscheint sie dort über
  dem Terminal (nicht nur im Dashboard).
- Wenn kein Submit kommt, dann bleibt die Frage nach Timeout offen und wird
  nicht erneut gestellt (Policy und Tool-Hinweis).

## Decisions

- D1, 2026-09-13: Ein Tool `show_ui` neben `ask_bo` statt eines neuen
  Panel-Schemas — HTML ist die universelle Beschreibung, Tailwind die
  Gestaltung; strukturierte Schnellfälle bleiben bei `ask_bo`.
- D2, 2026-09-13: Rendering im sandboxed iframe ohne Same-Origin; Tailwind als
  vendorierter Browser-Build (`src/assets/tailwind-browser.js`, 4.3.3) im
  Frame eingebettet, damit es offline und ohne CSP-Ausnahme läuft.
- D3, 2026-09-13: Antwortkanal = postMessage mit Interaktions-ID; die App
  ruft `ui_answer`. Nur die erste Antwort zählt.
- D4, 2026-09-13: Skill `agent-ui` als Workflow-Skill (Einrichten legt ihn an);
  gespeicherte UIs liegen als HTML-Dateien neben dem Skill und werden per
  absolutem `file` gezeigt.

## Tasks

- [x] `show_ui`/`ui_result` im Desktop-UI-MCP, `ui_answer`-Command, Registry mit Werten.
- [x] `HtmlInteractionCard` (iframe, Tailwind, Brücke, Höhe, Einfrieren, Schließen),
      Anbindung in `AskBoPanel`; Panel im Projektfenster über dem Terminal (Hook `useAskBo`).
- [x] Skill-Vorlage `agent-ui`, Policy v9 „Asking through the app UI“, `.agent/agent.md` gespiegelt.
- [x] Tests: Rust (Validierung, Warten, `show`, Datei, Timeout), Browser-Suite
      `test_agent_ui` (Tailwind wirksam, Werte, data-answer, show/close, Dashboard).
- [x] Hilfe, Playbook V1-06, UI-Baum.
- [x] App neu bündeln und mit echtem Agenten prüfen (`show_ui` aus dem Terminal).
      Gebündelt und gestartet; `tools/list` des Desktop-UI-MCP nennt `show_ui`/`ui_result`,
      ein echter `show_ui`-Aufruf (Modus `show`, Tabelle „Testlauf 038“) wurde
      angenommen und liegt in der App zur Sichtprüfung. Aufruf aus einem
      Claude/Codex-Terminal mit Formularantwort bleibt Deine Prüfung.

## Verification

2026-09-13:

- `cargo test -p speccify-desktop`: 109 bestanden, 3 ignoriert; neuer Test
  `show_ui_waits_for_form_values_and_supports_show_and_files` (Validierung
  von Modus/Datei, Blockieren bis `answer_values` mit Listenwerten, `show`
  kehrt sofort zurück und `ui_result` meldet `closed`, Datei wird gelesen,
  Timeout lässt die Karte offen). `cargo fmt --check`, `pnpm typecheck` grün.
- Browser-Suite `test_agent_ui` gegen den Mock: Formular mit Tailwind-Knopf
  (Hintergrundfarbe im Frame gesetzt, also Tailwind offline wirksam), Submit
  liefert `{target, services:[…], note, action}`, Karte zeigt „Antwort“;
  `data-answer` liefert `{answer:"no"}`; `mode: show` mit Tabelle, Schließen
  liefert `{closed:true}` und „geschlossen“; Dashboard rendert dieselbe Karte.
- Befund: Vite kann `@tailwindcss/browser/dist/index.global.js` nicht per
  Unterpfad laden (Exports); daher vendorierte Kopie unter `src/assets/`.
- Gebündelte App (neuer Build) läuft; Desktop-UI-MCP auf 18768 listet
  `show_ui`/`ui_result`; `show_ui` mit `mode: show` antwortet
  `{shown: true, interaction_id}` — die Karte „Testlauf 038“ steht in der App.
- Nicht geprüft: Formularantwort aus einem echten Claude/Codex-Terminal und
  die Sicht auf die Karte (BO). Deshalb `ready`.

## Questions

Keine.
