---
station: Backlog
order: 5
created: 2026-09-10
needs_human: true
ready: false
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

- [ ] Gemeinsames Kontextformat und Auftragsarten festlegen.
- [ ] Vorschau aus aktuellen Dateien und Projektregeln bilden.
- [ ] Einfügen/Kopieren über einen bestätigten Übergabeweg vereinheitlichen.
- [ ] Spec-/Playbook-/Skill-/Datei-Aktionen an diesen Weg anschließen.
- [ ] Zwei Fenster, fehlendes Terminal, Shell-Modus und mehrzeilige Eingabe prüfen.

## Verification

F9 in [006](../006-bestandsaufnahme-agent-terminal/SPEC.md), `lib/prompt.ts`,
`BoardTab.tsx` und der `speccify:type-command`-Listener in `TerminalPanel.tsx`.
Umsetzung und echte Zustellprüfung noch nicht durchgeführt.

## Questions

Keine blockierende Frage für den Entwurf.
