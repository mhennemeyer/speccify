---
station: Doing
order: 47
needs_human: true
ready: false
---

# Playbook-Drafts ohne Einfluss auf den Entwicklungsflow

## Why

Playbooks sollen auch Ideen und Recherche aufnehmen können, bevor daraus
geltende Arbeitsanweisungen werden. Bisher erscheinen alle Playbooks als
stehende Anleitungen und können gleichermaßen zur Ausführung übergeben werden.

## What

Optionales flaches Frontmatter `status: draft | active` in Liste, Editor,
Anlegen und Übergabe unterstützen. Ohne Feld gilt für bestehenden Bestand
`active`. Drafts bleiben normale versionierte Markdown-Dateien im selben
Playbook-Ordner; sie haben keine Board-Station und keinen Spec-Lifecycle.

Drafts sind sichtbar, lesbar und bearbeitbar, aber kein automatischer
Workflow-/Anweisungskontext. Sie werden nur bei ausdrücklicher Auswahl zur
Besprechung oder Bearbeitung übergeben, mit erhaltenem nichtbindendem Status.
Aktivierung ist eine ausdrückliche Statusaktion, nicht Folge von Speichern,
Öffnen, Verlinken oder einer allgemeinen Aufforderung, nach Playbooks zu arbeiten.

## Acceptance

- Ein vorhandenes Playbook ohne Status behält sein aktives Verhalten. Ein
  Playbook mit `status: draft` zeigt einen textlichen Draft-Hinweis in Liste,
  Detail und Inspektor, auch im gemeinsamen Workspace-Katalog.
- Beim Anlegen lässt sich Draft ausdrücklich wählen; der Standard für
  bestehende aktive Arbeitsabläufe bleibt kompatibel. Aktiv/Draft lässt sich
  gezielt ändern; nach Speichern und Wiederöffnen ist der Zustand erhalten.
- Ein unbekannter oder ungültiger Status wird sichtbar als prüfbedürftig
  behandelt und nicht still als aktive Anweisung ausgeführt.
- Editor-Autosave, unbekannte Metadaten und externe Änderungen erhalten den
  fachlichen Status. Ein ungespeicherter Editorentwurf ist sprachlich und
  funktional vom Playbook-Draft unterscheidbar.
- Automatische Workflow-Kontexte berücksichtigen aktive Playbooks. Drafts
  erscheinen darin höchstens als nichtbindende Verweise, nie als Anweisungen.
  Ein konkreter Review-/Bearbeitungsauftrag darf ihren Inhalt laden.
- Der normale Ausführen-/Übergabeweg aktiviert keinen Draft. Eine ausdrücklich
  ausgewählte Übergabe zur Besprechung/Bearbeitung trägt Titel, Herkunft,
  Draft-Status und nichtbindenden Zweck bis in den tatsächlich kopierten oder
  eingefügten Prompt. Frontmatter wird dabei nicht wirkungslos abgeschnitten.
- Repo-Guidance und Workflow-Vorlagen erklären die Semantik, einschließlich
  Umgang mit Altbestand. Individuelle Projektregeln werden nicht überschrieben.
- Der Web-App-Research-Draft bleibt nach dem App-Update ein Draft. Seine
  Vorschläge starten keine Specs oder automatischen Entwicklungsaufträge.

## Decisions

1. 2026-09-16: Nutzerauftrag zur einfachen Markierung als Draft.
2. 2026-09-16: Feld `status`, Werte `draft`/`active`; fehlendes Feld kompatibel
   aktiv. Keine zusätzliche Dateiablage, keine automatische Veröffentlichung.
3. 2026-09-16: Externe Hosts können Markdown selbst lesen; eine Statusmarkierung
   ist keine technische Zugriffssperre. Verbindliche Repo-Guidance plus
   statusbewusste Speccify-Kontexte/Übergaben setzen den gewünschten Vertrag um.
4. 2026-09-16: Der [Research-Draft](../../playbooks/speccify-web-app.md) nutzt die
   Konvention bereits mit sichtbarem Hinweis. UI-Unterstützung folgt erst hier.
5. 2026-09-16: Durch „leg los“ autorisiert. Nach 044 vorgezogen, damit der
   gemeinsame Wissenskatalog bereits statusbewusste Playbooks verwenden kann.

## Tasks

- [ ] Nativen Playbook-Vertrag um Status und kompatibles Parsing erweitern.
- [ ] Liste, Filter, Anlegen, Editor und explizite Statusaktion integrieren.
- [ ] Workflow-/Kontextauswahl und Handover für Drafts anpassen; Vorlagen nachführen.
- [ ] Statuspersistenz, Metadatenerhalt, ungültige Werte und echte Prompt-Übergabe prüfen.
- [ ] Hilfe und Produktplaybooks aktualisieren; Research-Draft in der App abnehmen lassen.

## Verification

Bestand: `PlaybookEntry` enthält `file`, `title`, `description`.
`PlaybooksTab.tsx` übergibt Playbooks ohne fachlichen Status an `HandoverButton`;
`handover.ts` besitzt nur den generischen Typ `playbook`. Die Repo-Regel aus
043 gilt bereits; App- und Vorlagen-Unterstützung ist noch nicht implementiert.

## Questions

Keine für den beschriebenen Umsetzungsschnitt.
