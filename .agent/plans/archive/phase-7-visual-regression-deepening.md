---
lifecycle: done
sessionId: phase-7-visual-regression-deepening
---
# Phase 7 (OPTIONAL) — Visual-Regression-Vertiefung + offene 5d-Punkte

> **Archiviert 2026-07-23 (OSS-Pivot, Entscheidung D4 im [P2-Plan](../phase-p2-api-composition-mocks.md)):** **S4** (`screenshots[].tolerance`) landet im P2-Schema-Bump (Spec-Schema v1, Stage 1). S1–S3 und S5–S7 bleiben optionales Backlog und können nach dem Composer (P3) einzeln gezogen werden — sie blockieren keine Pivot-Meilensteine.
>
> **Status:** Entwurf (2026-06-02), **optional**. Sammelbecken für die in Phase 5c offen gebliebenen 5d-Kandidaten.
> **Reihenfolge:** Nach Phase 6 (Landingpage + Doku). Kann ganz übersprungen oder in mehrere Mini-Phasen zerlegt werden — je nach Außenwirkung von Phase 6.
> **Ziel-Tag (falls gemacht):** `v0.12.0-phase-7` (Vorschlag).
> **Begründung als „optional":** Die in 5c gebaute Visual-Regression ist bereits ein lauffähiges Skeleton mit 1 Referenz-PNG. Eine Vertiefung ist wertvoll, blockiert aber keine Vision-relevanten Meilensteine (Marketplace, weitere Targets, Adoption). Dieser Plan stellt sicher, dass die Punkte **nicht verloren gehen**.

## Hintergrund

In Phase 5c wurden 7 Folge-Kandidaten identifiziert. Sie werden hier als **eigenständig wählbare Substages** (S1–S7) festgehalten, sodass jede einzeln gezogen oder vertagt werden kann.

## Substages (alle optional, in beliebiger Reihenfolge)

### S1 — Volle Visual-Regression-Coverage (React + Angular)
**Was:** 5 Phase-0-Specs × {React, Angular} = 10 Referenz-PNGs in `specs/screenshots/` einchecken; bestehender `PlaywrightPixelmatchDriver` läuft pro Kombination.
**Aufwand:** M (Referenz-PNGs vom Maintainer erzeugen + sauberer Snapshot-Workflow).
**Voraussetzung:** S3 (`--update-snapshots`) ist hier sehr hilfreich.
**Done:** 10 E2E-`visual_regression`-Tests grün im CI-Workflow `.github/workflows/visual-regression.yml`.

### S2 — Echter Component-Mount-Renderer
**Was:** Aktuelle Sandbox rendert generierten Code in `<pre>`. Ersetze durch einen echten Mount-Punkt:
- React: Vite-basierter Mount in einer Sandbox-HTML-Seite.
- Angular: Standalone-Component-Mount via `bootstrapApplication`.
- Playwright schießt das gemountete DOM.
**Aufwand:** L (neue Renderer-Pipeline, Hot-Reload-Loop für lokale Entwicklung).
**Risiko:** Build-Tooling-Reibung; Replay-Cache muss kompatibel bleiben.
**Done:** Visual-Regression-Tests laufen gegen echtes Render-Resultat, nicht `<pre>`.

### S3 — `--update-snapshots` Pytest-Flag
**Was:** Pytest-Hook `--update-snapshots`, der bei Diff die neue PNG schreibt statt zu failen.
**Aufwand:** S.
**Done:** Maintainer kann mit einem Befehl alle Snapshots regenerieren; CI bleibt strikt (Flag nur lokal).

### S4 — Schema-Bump `screenshots[].tolerance` (v2 → v3)
**Was:** Optionales Feld `tolerance` pro Screenshot in `speccify.yaml`. JSON-Schema v3, Validator-Update, Lockfile-Kompatibilitätspfad.
**Aufwand:** M (Schema-Migration + Migrations-Test + Lockfile-Bump-Erwägung).
**Done:** `screenshots[].tolerance` als Override gegen Default-10 % funktional, alle bestehenden Specs v2-kompatibel auflösbar.

### S5 — SwiftUI-Visual-Regression via Xcode-UI-Tests
**Was:** Dritter `VisualDiffDriver` für SwiftUI, basierend auf `xcrun simctl` + Xcode-UI-Test-Runner; macOS-only.
**Aufwand:** L (Xcode-Toolchain, Simulator-Setup im CI macOS-Runner).
**Voraussetzung:** Phase 5a SwiftUI-Build-Smoke läuft schon.
**Done:** Mindestens `button` mit SwiftUI-Visual-Regression grün.

### S6 — Echtes `ng build` statt `tsc --noEmit`
**Was:** Angular-Toolchain-Driver auf vollen `ng build`-Pfad upgraden (Webpack-Bundle, AOT). Phase 5a hatte das bewusst auf `tsc --noEmit` reduziert.
**Aufwand:** M (CI-Zeit + Toolchain-Pin `@angular/cli`).
**Done:** `AngularToolchainDriver` benutzt `ng build`; CI-Conformance-Job läuft weiter unter 10 min.

### S7 — Web-Backend Workspace-aware
**Was:** `speccify-web-backend` (Phase 1d) verarbeitet aktuell nur Single-Spec-Requests. Workspace-Modus: `workspace_root` als Request-Parameter, ruft `Workspace.lock`/`Workspace.pull` analog zur MCP-Bridge (Phase 4).
**Aufwand:** M.
**Done:** Playground-Frontend kann ein Mehr-Member-Workspace-Manifest hochladen und gerenderte Outputs pro Member sehen.

## Stage 0 (falls Phase 7 gestartet wird)
- User wählt explizit, welche Substages **in diesem Durchlauf** gemacht werden (mindestens 1, beliebig viele).
- Pro gewählter Substage werden bei Bedarf eigene Open Questions als Block vorgelegt (z. B. macOS-CI-Runner-Kosten für S5).

## Erfolgs-/Done-Kriterien (pro Substage individuell)
Jede Substage hat ihr eigenes „Done" oben. Eine Phase 7 ist „abgeschlossen", sobald die in Stage 0 gewählten Substages erledigt sind — alle anderen bleiben im Plan stehen für eine spätere Phase-7-Iteration (oder Phase 9+).

## Out-of-Scope (auch innerhalb Phase 7)
- Marketplace / Billing — bleibt Master-Plan-on-hold.
- Tauri-Desktop — bleibt geparkt.
- Figma-Integration — Phase 9+.

## Cross-Referenzen
- Master-Plan: `.agent/plans/speccify-plan.md`
- Archiv Phase 5c: `.agent/plans/archive/phase-5c-visual-regression-skeleton.md`
- Vorgänger: `.agent/plans/phase-6-landing-and-docs.md`
