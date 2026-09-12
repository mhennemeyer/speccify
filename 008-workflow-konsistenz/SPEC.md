---
station: Doing
order: 2
created: 2026-09-10
needs_human: true
ready: true
open_question: null
parent: null
---
# Workflow-Einweisung und Spec-Darstellung konsistent machen

## Why

Ein Agent kann den Workflow nur zuverlässig befolgen, wenn seine tatsächliche
Einweisung vollständig ist und das Board dieselbe Arbeit darstellt. Heute
fehlen im eigenen Repo Workflow-Skills; Links werden zu oberflächlich geprüft,
und Beispiel-Checkboxen können echte Aufgaben werden.

## What

Die in Spec 005 gelieferte Funktion gezielt härten: Setup-Status, Linkziele,
Versionierung der Workflow-Skills, Vorrang von Projektregeln sowie konsistente
Task-Erkennung und Bearbeitung. Das eigene Repo danach als Referenz einrichten.
Die offene menschliche Abnahme von 005 bleibt dort erhalten.

Keine neue Board-Architektur, keine neue Workflow-Sprache und keine
stillschweigende Überschreibung individuell angepasster Anweisungen.

## Acceptance

- Wenn ein Skill-Link defekt ist oder auf ein anderes Verzeichnis zeigt,
  meldet das Setup die genaue Abweichung und behauptet nicht `current`.
- Wenn Workflow-Skills fehlen, veraltet oder individuell angepasst sind,
  unterscheidet die Diagnose diese Zustände. Ein erneutes Setup erhält
  Anpassungen und ändert unbeteiligte Inhalte nicht.
- Wenn ein Projekt Commit/Push bereits erlaubt oder Herkunftsangaben verbietet,
  fügt das Setup keine gegenteilige wirksame Regel hinzu.
- Wenn eine Spec Beispiel-Checkboxen innerhalb von Markdown-Codeblöcken
  enthält, ignorieren Fortschritt, Task-Liste und Umschalten diese Beispiele.
  Alle drei verwenden dieselbe Definition und treffen dieselbe echte Aufgabe.
- Wenn eine Datei zwischen Anzeige und Task-Klick verändert wird, geht keine
  fremde Änderung verloren und es wird nicht die inzwischen andere Aufgabe
  am alten Index umgeschaltet; nötigenfalls wird neu geladen.
- Wenn eine neue Sitzung im Speccify-Repo beginnt, findet sie `spec-next`,
  `spec-ask` und die geltenden Regeln; historische Statusdateien sind erkennbar.

## Decisions

- D1 (2026-09-10): Delta zu Spec 005; bestehende Migration und UI weiterverwenden.
- D2 (2026-09-10): Format von bestehenden Specs erhalten. Den Umgang mit
  Checkboxen außerhalb von `## Tasks` bei Umsetzung ausdrücklich festlegen;
  Codebeispiele dürfen in keinem Fall als bearbeitbare Aufgaben gelten.
- D3 (2026-09-10): Setup erkennt Konflikte und bietet gezielte Reparaturen;
  persönliche Konfigurationen werden nicht pauschal ersetzt.
- D4 (2026-09-10): Fortsetzungsauftrag startet Spec 008. Tasks sind Markdown-
  Aufgabenlisten im gesamten Body (Bestandskompatibilität), nicht ausschließlich
  unter Tasks. Codeblöcke zählen nicht. Ein nativer Markdown-Parser liefert
  Liste, Zähler und Byteposition für den Klick; kein zweiter Frontend-Parser.
- D5: Checkbox-Klick sendet den angezeigten Body als erwarteten Stand. Bei
  abweichendem Body verweigern und neu laden; frisches Frontmatter erhalten.
  Optimistische Konfliktprüfung, keine Dateisperre gegenüber beliebigen Editoren.
- D6: Nur bekannte unveränderte Policy-/Skill-Vorlagen automatisch aktualisieren.
  Angepasste/neue unbekannte Versionen oder beschädigte Marker manuell prüfen.
  Link-Hülsen nur bei exakt passendem Ziel ersetzen, fremde Verzeichnisse bewahren.

## Tasks

- [x] Setup-Diagnose für Linkziel, Skill-Version und Anpassungen ergänzen.
- [x] Workflow-Vorlagen mit dem Vorrang ausdrücklicher Projektregeln vereinbaren.
- [x] Gemeinsamen Task-Vertrag für Zähler, UI und Schreiboperation festlegen.
- [x] Codeblöcke und zwischenzeitliche Änderungen in der Task-Bearbeitung abdecken.
- [x] Eigenes Repo kontrolliert einrichten und alte Einstiegspunkte einordnen.
- [x] Setup zweimal sowie mit angepassten Dateien und defekten Links prüfen.

## Verification

Ausgangsbefunde F2–F5 in [006](../006-bestandsaufnahme-agent-terminal/SPEC.md).

Prüfung am 2026-09-10:

- `cargo test --workspace`: 105 bestanden, 2 ignoriert. Die neun normalen
  Setup-Tests prüfen bekannte Policy-Versionen 1–3, wiederholtes Setup,
  angepasste/unbekannte/beschädigte Blöcke, defekte/fremde Links und Schutz
  vor Schreiben durch verlinkte Projektverzeichnisse.
- Native Parser-/Board-Tests: Backtick-/Tilde-/eingerückte Codeblöcke,
  verschachtelte und nummerierte Aufgaben, CRLF/UTF-8, gemeinsame DTO-Zähler
  sowie veraltete Klicks ohne Datei-/History-Änderung. Ein frisches Frontmatter
  bleibt beim gültigen Body-Snapshot erhalten.
- `SPECCIFY_CHECK_PROJECT=<Repo> cargo test -p speccify-desktop
  check_project_from_env -- --ignored --nocapture`: zusätzlich explizit
  ausgeführte Nur-Lese-Diagnose am eigenen Checkout meldet `current`,
  installed/current v4, keine offenen Befunde. Der andere ignorierte Test
  ist der bestehende lokale KB-Test.
- Beide kanonischen Workflow-Skills mit `quick_validate.py` validiert;
  Anpassung beschränkt auf Versionierung und Vorrang der Projekt-/Hostregeln.
  Bestehende Projekttexte und Skill-Adapter erhalten.
- `pnpm --filter speccify-desktop typecheck`, `cargo fmt --check` und
  `git diff --check`: bestanden.
- `scripts/test_workflow_ui.mjs` mit lokalem Chrome/Playwright gegen isoliertes
  Vite-Mock auf 1421: strukturierte Setup-Befunde, selektives Einrichten,
  rein manuelle Konflikte ohne Installationsknopf, kein v4→v4-Hinweis;
  veralteter Task-Klick wird sichtbar abgewiesen, lädt neu, erneuter Klick
  aktualisiert Liste und Zähler. Testselektoren für Tab-Rolle und absichtlich
  unveränderte Checkbox korrigiert; abschließender Lauf vollständig grün.
- `scripts/test_action_output.mjs`: bestehende Ausgabetab-Regression in beiden
  Dock-Layouts vollständig grün, einschließlich Stop/Fehler, Wiederholung,
  parallelen Aktionen, Output-Limit und fehlgeschlagenem Listener.
- `bash scripts/dev.sh --app --prepared --ui-port=18768`: lokaler Debug-Build
  erfolgreich, neue App PID 30441 gestartet; gebündelte Binärdatei stimmt per
  `cmp` mit dem Build überein. Bekannte Vite-Chunkgrößenwarnung, keine Release-
  Signierung/Veröffentlichung. Separater Testserver auf 1421 danach beendet.
- Live-HTTP-Smoke: Initialize/initialized/tools-list und alle zehn negativen
  Grenzfälle bestanden. Das allein bestätigt keine bedienbare Oberfläche.
- Wiederaufnahme am 2026-09-10 17:15 UTC noch nicht bestätigt: macOS zeigt
  sichtbar „Speccify möchte Zugriff auf Dateien in deinem Ordner Schreibtisch“.
  Stack-Sample erklärt den wartenden UI-Thread durch `policy_state` → Datei-
  `open`; keine Freigabe automatisiert. Die drei gespeicherten Projektpfade
  AVC, iKanban und speccify sind erhalten. App und Systemdialog bleiben offen.
  Nach menschlichem „Erlauben“ Fenster und Terminal-Fortsetzung prüfen; die
  vorige Terminal-Sitzung lief mit `resume --last`, exakte Fortsetzung unbewiesen.

UI-Prüfungen verwenden isolierte Transport-Fixtures; echte Markdown-/Datei-
Semantik wird separat nativ getestet. Das ist keine menschliche App-Abnahme.
Die Body-Prüfung ist optimistisch: ein beliebiger externer Editor kann noch
zwischen letztem Lesen und Rename schreiben; keine systemweite Dateisperre.

## Questions

Implementierung bereit zur menschlichen Abnahme (`Doing`, `ready: true`).
Für die lokale Wiederaufnahme den sichtbaren macOS-Dialog bestätigen, sofern
der Zugriff gewünscht ist. Keine neue Produktentscheidung erforderlich.
