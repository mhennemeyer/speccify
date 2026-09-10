---
station: Backlog
order: 4
created: 2026-09-10
needs_human: false
ready: false
open_question: null
parent: null
---
# CLI und MCP liefern denselben vollständigen Prüfstatus

## Why

`verify` zeigt in der CLI fehlende Tool-Implementierungen, während MCP diese
Information verwirft. Ein konsistentes Lockfile ist nicht gleichbedeutend mit
ausführbaren und geprüften Werkzeugen. Mensch und Agent brauchen dieselben Fakten.

## What

Ein strukturierter Verify-Vertrag für Lockfile-/Bundle-/Expansions-Drift,
fehlende Implementierung, noch nicht geprüfte Implementierung und Plattform.
CLI erhält JSON-Ausgabe, MCP liefert dieselben Felder aus derselben fachlichen
Berechnung. Den vorhandenen `ExpansionStatus` nutzen und Unterschiede zwischen
Fehler, Hinweis und Einsatzbereitschaft ausdrücklich dokumentieren.

Liefert die Voraussetzung für die offene Anzeige aus Spec 004. Deren
Quellversions-UI bleibt dort; kein zweites paralleles Update-System entwickeln.
Keine Implementierung der drei Bibliotheks-Tools als Nebenaufgabe.

## Acceptance

- Wenn ein Lockfile konsistent ist, aber ein Tool fehlt, nennen CLI-Text,
  CLI-JSON und MCP dieselbe Plattform und denselben fehlenden Toolnamen.
- Wenn ein Tool existiert, aber nicht geprüft ist, unterscheidet sich das
  Ergebnis vom fehlenden Tool und vom erfolgreich geprüften Tool.
- Wenn Drift vorliegt, wird sie als Fehler ausgewiesen; eine bisher grüne
  Tool-Markierung verdeckt die Abweichung nicht.
- Wenn ein Client die neuen Felder noch nicht kennt, bleibt die bisherige
  Bedeutung von `ok` kompatibel und dokumentiert; ein neuer expliziter Status
  kann vollständige Einsatzbereitschaft ausdrücken.
- Wenn `verify` läuft, führt es keine Tool-Beispiele aus und schreibt keinen
  Verifikationsstatus. `tool check` bleibt der Ausführungs- und Prüfweg.

## Decisions

- D1 (2026-09-10): Bestehendes Ergebnis erweitern, statt `ok` still umzudeuten.
- D2 (2026-09-10): Fachliche Berechnung gemeinsam halten; Adapter formatieren
  Ergebnisse. Die Vertragsfelder werden vor Implementierung festgelegt.

## Tasks

- [ ] Statusschema und Kompatibilität festlegen.
- [ ] Gemeinsamen Verify-Bericht aus vorhandenen Daten bereitstellen.
- [ ] CLI-JSON und MCP auf denselben Bericht führen.
- [ ] Matrix konsistent/fehlend/ungeprüft/geprüft/Drift mit vorhandenen Fixtures testen.
- [ ] Dokumentation und Anschlussvertrag für Spec 004 aktualisieren.

## Verification

F8 in [006](../006-bestandsaufnahme-agent-terminal/SPEC.md).
`cli/commands/verify.py:run_verify` verwirft den zweiten Rückgabewert von
`run_verify_with_status`; `mcp/tools/project.py:run_verify` nutzt genau diesen
reduzierten Weg. Umsetzung noch nicht geprüft.

## Questions

Keine blockierende Frage für den Entwurf.
