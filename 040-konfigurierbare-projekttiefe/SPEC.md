---
station: Done
order: 40
needs_human: true
ready: true
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

4. 2026-09-15: Nutzerabnahme im Chat: „Sieht soweit gut aus.“ Anschließend
   Veröffentlichung mit neuem Release und Website-/Doku-Aktualisierung beauftragt.

1. 2026-09-15: Nutzerauftrag ersetzt den festen Standard aus Spec 025. Die Tiefe
   zählt vom geöffneten Root aus; dessen eigener Projektkontext bleibt erhalten.
2. 2026-09-15: Einstellung im Dashboard unter Einstellungen. Gilt beim Öffnen,
   erneuten Erkennen und Aktualisieren gespeicherter Workspace-Ansichten.
   Tiefe ist ein Suchumfang, kein Fehler und keine Dateilöschaktion.
3. 2026-09-15: Bindungen bleiben intern gespeichert; Darstellung, Board und
   Startkontext werden gefiltert. Laufende Ziele behalten ihre Pfadbindung.

## Tasks

- [x] Native Einstellung, Suchgrenze und gefilterte Workspace-Verträge implementieren.
- [x] Einstellung in der UI und Erhalt geöffneter Entwürfe umsetzen.
- [x] Regressionen, Typecheck und Rust-Prüfungen durchführen.
- [x] Dokumentation/Playbooks aktualisieren; lokale App aktualisieren und AVC prüfen.
- [x] Mit Nutzeridentität committen und synchronisieren.

## Verification

- `cargo test -p speccify-desktop`: 117 bestanden, 3 opt-in ignoriert.
- `cargo fmt --check`, `pnpm --filter speccify-desktop typecheck`, `git diff --check`: grün.
- `node scripts/test_workspace_depth.mjs`: Standard 1, Einstellung speichern/reload,
  verschachteltes Projekt 3 → 1 → 3 mit erhaltenem Commit-Entwurf.
- `node scripts/test_workspace_shell.mjs`, `node scripts/test_workspace_ui.mjs`: grün.
- Gebündelte lokale App aktualisiert, vier Fenster wiederhergestellt; PID 93486,
  UI-Port 18768, QA-Port 18769, kein Vite auf 1420. Signatur außerhalb der
  Ausführungssandbox mit `codesign --verify --deep --strict --verbose=4` gültig.
- Native QA-Brücke: AVC zeigt bei 1 genau Root-Kontext, billi-ci, billi-legacy,
  rekas. Bei 3 erscheinen beide externen billi-legacy-Klone mit denselben IDs.
  Abschließend 1 gespeichert und erneut erkannt: keine Warnung, Board und
  Startkontext ohne externe Klone. Projekte und Bindungen im Store unverändert.
- Native Bildschirmaufnahme scheiterte am macOS-Aufnahme-Rechteck; sichtbare
  Gruppen wurden stattdessen im DOM der laufenden App geprüft.
- Commit `5c30726` auf `main`, Autor und Committer Matthias Hennemeyer
  <mhennemeyer@me.com>; `git pull --ff-only origin main` aktuell,
  anschließend `git push origin main` erfolgreich.

## Questions

Keine.
