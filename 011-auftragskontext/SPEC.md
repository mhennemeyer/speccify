---
station: Doing
order: 5
created: 2026-09-10
needs_human: true
ready: true
open_question: null
parent: null
---
# Aus einer Auswahl einen eindeutigen Auftrag machen

## Why

Eine in der UI ausgewählte Spec oder Datei ist nicht automatisch im Kontext
des Agenten. Kopierter Markdown-Text und unbestätigte Terminal-Events reichen
nicht aus, um Projekt, Auftrag und Zustellung zuverlässig zu unterscheiden.

## What

Gemeinsamer Übergabeweg für Specs, Playbooks, Skills und Dateien: ausgewähltes
Projekt, Pfad, bei Specs ID und aktueller Status, Nutzerabsicht und Hinweis auf
die geltenden Projektregeln. Zuerst eine sichtbare Prompt-Vorschau mit robustem
Einfügen/Kopieren verwenden. Eine neue MCP-Kontext-API ist für diese Spec nicht
erforderlich. Abhängigkeiten: Start-/Terminalverträge aus 007 und 009.

Die App startet nicht allein durch Auswahl oder Board-Verschieben einen Auftrag.
Keine automatische Agent-Orchestrierung, kein Upload des gesamten Projekts.

## Acceptance

- Wenn „Spec umsetzen“ gewählt wird, enthält die Vorschau Projektwurzel,
  Spec-ID/Pfad, aktuellen Status und einen klaren Umsetzungsauftrag. „Prüfen“
  formuliert einen Prüfauftrag mit passendem Umfang.
- Wenn die Spec nach Auswahl geändert wurde, wird vor der Übergabe der
  aktuelle Dateiinhalt gelesen oder die Abweichung angezeigt. Die Datei bleibt
  als Quelle der Wahrheit referenziert.
- Wenn nur die Board-Station oder Auswahl geändert wird, werden keine
  Terminaleingaben und keine Befehle automatisch abgeschickt.
- Wenn kein passendes Agent-Terminal bereit ist, meldet die UI die fehlende
  Zustellung und bietet Kopieren oder den bewussten Start an.
- Wenn mehrzeiliger Text mit Sonderzeichen übergeben wird, bleibt er eine
  zusammengehörige Eingabe. In einer reinen Shell wird er nicht versehentlich
  als Befehlsfolge ausgeführt. Absenden ist eine bewusste Nutzeraktion.
- Wenn zwei Projektfenster offen sind, erreicht der Auftrag ausschließlich
  das zugehörige Terminal; Erfolg wird erst nach bestätigtem Einfügen angezeigt.

## Decisions

- D1 (2026-09-10): Bestehende Pfad-/Markdown-Übergabe weiterverwenden und um
  eindeutige Absicht und Zustellstatus ergänzen.
- D2 (2026-09-10): Die ältere `viewer_selection`-API wird nicht als
  Desktop-Kontext ausgegeben; sie bedient einen anderen Viewer.

## Tasks

- [x] Gemeinsames Kontextformat und Auftragsarten festlegen.
      `lib/handover.ts`: Kopf (Projekt, Art/ID/Station, Pfad als Quelle der
      Wahrheit, Auftrag, Regelverweis) + Datei als Zaun; Absichten
      `implement`/`review`/`read` (Specs) und `read`/`edit` (Rest).
- [x] Vorschau aus aktuellen Dateien und Projektregeln bilden.
      `HandoverSheet`: liest die Datei beim Öffnen und erneut vor der Zustellung,
      Abweichungshinweis gegen den zuletzt angezeigten Stand, Text editierbar.
- [x] Einfügen/Kopieren über einen bestätigten Übergabeweg vereinheitlichen.
      `registerTerminalWriter`/`deliverToTerminal` mit Ergebnis
      (delivered/no-terminal/error); mehrzeilig als Bracketed Paste ohne
      abschließendes Enter; `speccify:type-command` läuft über denselben Weg.
- [x] Spec-/Playbook-/Skill-/Datei-Aktionen an diesen Weg anschließen.
      „Auftrag…“ ersetzt „Als Prompt kopieren“ in Board, Playbooks, Skills,
      Tools und Agent-Dateien; Skill-Import/-Export und Commit-Auftrag melden
      Zustellung oder fehlendes Terminal.
- [x] Zwei Fenster, fehlendes Terminal, Shell-Modus und mehrzeilige Eingabe prüfen.
      Zwei Fenster: der Schreiber ist je Fenster registriert (JS-Kontext), im
      Workspace nur für das aktive Projekt (Fehler statt Fremdzustellung).

## Verification

Ausgangsbefund F9 in [006](../006-bestandsaufnahme-agent-terminal/SPEC.md):
Board kopierte Pfad+Body, andere Tabs feuerten `speccify:type-command` ohne
Rückmeldung.

2026-09-13:

- `pnpm typecheck` grün. Browser-Suite `test_handover` gegen den Mock:
  Vorschau nennt Projektwurzel, Spec-ID mit Station, Pfad, Auftrag „Arbeite
  diese Spec…“ und Regelverweis; ohne Terminal keine Eingabe, Hinweis und
  „Terminal starten“; nach Start „bereit“; Absicht „Prüfen“ ändert den
  Auftrag; Zustellung ist genau ein Bracketed-Paste-Block ohne `\r`;
  nachträglich geänderte Datei → Hinweis und aktueller Inhalt; Auswahl und
  Boardwechsel schicken nichts. Die 14 übrigen Suiten (u. a. Workspace-Shell
  mit Commit-Auftrag ans geteilte Terminal, Git-Workspace) bleiben grün.
- Nicht geprüft: echte Zustellung an Claude/Codex in der gebündelten App
  (Bracketed Paste im Host; in zsh/bash ≥ 5.1 Standard) und Shell-Modus mit
  altem Shell ohne Bracketed Paste. Deshalb `ready`.

## Questions

Keine blockierende Frage für den Entwurf.
