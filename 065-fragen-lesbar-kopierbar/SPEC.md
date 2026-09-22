---
station: Done
order: 65
created: 2026-09-22
modules: board
---
# Agent-Fragen lesbar: Markdown, Absätze, Code zum Kopieren

## Why

BO 2026-09-22 (Screenshot aus einem Projekt-Board, Frage Q1 zu Spec 008):
Fragen des Agenten erscheinen als ein Textblock. Befehle, Pfade und Namen,
die der Mensch in ein Terminal übertragen muss, stehen in Backticks mitten im
Fließtext und lassen sich nur mühsam markieren. Gewünscht: solche Stellen
hervorheben und mit einem Knopf zum Kopieren versehen, dazu mehr Struktur
(Absätze, Listen).

## What

- Fragen und Antworten in der Frage-Box des Spec-Inspektors werden als Markdown
  gerendert (Absätze, Listen, Fett, Codeblöcke); einzelne Zeilenumbrüche des
  Agenten bleiben als Umbrüche erhalten.
- Inline-Code (`…`) und Codeblöcke bekommen einen Kopieren-Knopf, der den
  Inhalt in die Zwischenablage legt und kurz „kopiert“ zeigt.
- Außerhalb: Policy-Änderung (der Agent darf Markdown ohnehin), Fragen an
  anderen Stellen (Workspace-Board, Web-Board), Änderungen am Frage-Format.

## Acceptance

- Wenn eine Frage Absätze, eine Liste und Backticks enthält, dann zeigt die
  Box Absätze, Listenpunkte und hervorgehobenen Code statt eines Blocks.
- Wenn neben einem Code-Stück „Kopieren“ geklickt wird, dann liegt genau
  dieser Text (ohne Backticks) in der Zwischenablage und der Knopf zeigt „kopiert“.
- Wenn die Frage nur Fließtext ist, dann sieht sie aus wie bisher.

## Decisions

1. 2026-09-22: Rendern mit dem vorhandenen `Markdown`-Stack (react-markdown +
   GFM), eigene `code`/`pre`-Komponenten mit Kopierknopf; keine neue Abhängigkeit.
   Einzelne Umbrüche werden vor dem Rendern zu harten Umbrüchen, damit die
   Struktur des Agententexts nicht verloren geht.
2. 2026-09-22: Kein Release im selben Schritt; lokaler Build für BO, Release
   auf Zuruf.

## Tasks

- [x] `QuestionText`-Komponente (Markdown + Kopierknöpfe), in der Frage-Box für Frage und Antworten.
- [x] Mock: Clipboard-Kommando und Frage mit Markdown (`?qmd=1`); Regression `test_spec_questions.mjs`.
- [x] Typecheck, Nachbar-Suiten.
- [x] Lokaler Build und Neustart der App (0.8.5-Bundle aus `main` `14e5806`).
  App per Quit beendet (kein Terminal aktiv), `dev.sh --app --prepared --skip-engine`,
  neu gestartet mit vier Fenstern; Bundle enthält die Komponente.

## Verification

2026-09-22, Commit `14e5806`:

- `pnpm --filter speccify-desktop typecheck` ohne Befund.
- `test_spec_questions` ok: vier Absätze, zwei Listenpunkte, ein Codeblock, ein
  harter Umbruch, drei Inline-Code-Stellen mit je einem Knopf plus Block-Knopf;
  Klick schreibt exakt den Code (ohne Backticks) über
  `plugin:clipboard-manager|write_text`, Knopf zeigt „✓ kopiert“ und fällt zurück;
  reine Textfrage bleibt ein Absatz ohne Knöpfe. Gegen den alten `BoardTab.tsx`
  schlägt die Suite fehl. Nachbarn grün: `test_spec_navigation`,
  `test_team_signals`, `test_spec_modules`.
- Sichtprüfung im Mock (Screenshot): Kopierknopf des Blocks lag zunächst über dem
  Code → `padding-right` mit höherer Spezifität, nachgeprüft 88 px.
- Lokale App neu gebaut und gestartet (pid neu, vier Fenster, `codesign` ok);
  das gebündelte Frontend enthält `data-question-text`/`data-copy-code`. Eine
  offene Frage gibt es in diesem Repo gerade nicht — die Sichtprüfung in der
  echten App macht BO an der Frage zu Spec 008 im anderen Projekt.
- Nicht veröffentlicht: kommt mit dem nächsten Release (Entscheidung 2).

## Questions
