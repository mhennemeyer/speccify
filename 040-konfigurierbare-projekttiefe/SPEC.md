---
station: Doing
order: 40
needs_human: true
ready: false
---

# Konfigurierbare Projekt-Erkennungstiefe

## Why

AVC zeigt externe Referenzklone neben den eigentlichen Projekten. Die bisherige
feste Suchtiefe 16 erfasst für den normalen Einstieg zu viele Unterprojekte.

## What

Globale Einstellung für Projekt-Erkennungstiefe, Standard 1. Bestehende
Workspace-Ansichten berücksichtigen die Grenze, ohne Projektdateien zu ändern.

## Acceptance

- Ohne gespeicherte Einstellung werden Root (Tiefe 0) und direkte Unterordner
  (Tiefe 1) erkannt. Referenzklone in Tiefe 3 bleiben ausgeblendet.
- Die globale Einstellung erlaubt ganze Werte 1–16 und bleibt nach Neustart erhalten.
- Erneutes Erkennen berücksichtigt die Einstellung. Eine gewählte Tiefengrenze
  erzeugt keine Warnung; tatsächliche Budget-/Lesefehler bleiben sichtbar.
- Gespeicherte tiefe Bindungen werden ausgeblendet; beim Erhöhen bleiben ihre
  IDs, Namen und Gruppen erhalten. Bereits geöffnete Entwürfe bleiben erhalten.
- Dateien, Board und Kontext verwenden denselben sichtbaren Projektumfang.

## Decisions

1. 2026-09-15: Nutzerauftrag ersetzt den festen Standard aus Spec 025. Die Tiefe
   zählt vom geöffneten Root aus; dessen eigener Projektkontext bleibt erhalten.
2. 2026-09-15: Einstellung im Dashboard unter Einstellungen. Gilt beim Öffnen,
   erneuten Erkennen und Aktualisieren gespeicherter Workspace-Ansichten.
   Tiefe ist ein Suchumfang, kein Fehler und keine Dateilöschaktion.
3. 2026-09-15: Bindungen bleiben intern gespeichert; Darstellung, Board und
   Startkontext werden gefiltert. Laufende Ziele behalten ihre Pfadbindung.

## Tasks

- [ ] Native Einstellung, Suchgrenze und gefilterte Workspace-Verträge implementieren.
- [ ] Einstellung in der UI und Erhalt geöffneter Entwürfe umsetzen.
- [ ] Regressionen, Typecheck und Rust-Prüfungen durchführen.
- [ ] Dokumentation/Playbooks aktualisieren; lokale App aktualisieren und AVC prüfen.
- [ ] Mit Nutzeridentität committen und synchronisieren.

## Verification

Ausstehend.

## Questions

Keine.
