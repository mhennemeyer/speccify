---
station: Done
order: 4
created: 2026-09-10
needs_human: false
ready: true
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

- [x] Statusschema und Kompatibilität festlegen.
      `VerifyReport`: `ok` (unverändert: Lock/Manifest/Bundles/Expansions
      konsistent), `ready` (ok und jedes Tool für `platform` implementiert und
      geprüft), `platform`, `problems`, `tools: [{name, state:
      missing|unverified|verified}]`, `notes`, `error`.
- [x] Gemeinsamen Verify-Bericht aus vorhandenen Daten bereitstellen.
      `run_verify_report` in `speccify_cli.commands.verify` über
      `run_verify_with_status` + `ExpansionStatus` + `expansions.yaml`.
- [x] CLI-JSON und MCP auf denselben Bericht führen.
      `speccify verify --json --platform`, MCP `verify(platform)` liefert
      `VerifyResult` mit denselben Feldern (+ `code`/`message`).
- [x] Matrix konsistent/fehlend/ungeprüft/geprüft/Drift mit vorhandenen Fixtures testen.
- [x] Dokumentation und Anschlussvertrag für Spec 004 aktualisieren.
      CLI-Referenz regeneriert; Spec 004 kann `tools[].state` und `ready` für
      die Quellversions-UI lesen (Vertrag hier, kein zweites Update-System).

## Verification

Ausgangsbefund F8 in [006](../006-bestandsaufnahme-agent-terminal/SPEC.md):
`run_verify` verwarf den `ExpansionStatus`; MCP nutzte genau diesen Weg.

2026-09-13:

- `pytest` (alle Pakete) grün. Neu: CLI-Test über die Matrix mit der
  Notarize-Fixture (Plattform macos gepinnt): konsistent + Tool fehlend → `ok`
  true, `ready` false, `tools=[missing]`, Text nennt Plattform und Hinweis;
  Implementierung ohne Prüfung → `unverified`; nach `tool check` → `verified`,
  `ready` true, `notes` leer; `verify` schreibt nichts in `expansions.yaml`
  und führt keine Beispiele aus (Record vor/nach identisch); Upstream-Drift →
  `ok` false, `ready` false, Tool bleibt als `verified` gelistet (kein
  Verdecken); kaputtes Projekt → JSON mit `error`, Exit 1. MCP-Test: `verify`
  liefert dieselben Felder wie `speccify verify --json` (Feld für Feld
  verglichen), Fehlerfall `code: verify_failed`.
- `ruff check`/`format`, CLI-Referenz-Drift grün.
- Nicht geprüft: die Anzeige in der App (Spec 004 offener UI-Rest) — dort
  gehört der Anschluss hin; Windows-Plattformwerte in der Matrix.

## Questions

Keine blockierende Frage für den Entwurf.
