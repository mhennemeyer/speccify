# Referenz-Screenshots

Verzeichnis-Konvention für Visual-Regression (Phase 5c).

Spec-Manifeste referenzieren Screenshots relativ via `screenshots:`-Feld
(siehe `specs/button.speccify.yaml`), z. B. `./screenshots/button-primary.png`.
Dieses Verzeichnis hält die committed Referenz-PNGs, gegen die
`VisualRegressionBackend` diffed.

## Status (Skeleton)

Phase 5c Skeleton-Scope: **1 Referenz-PNG** als End-to-End-Proof reicht.
Voller Sweep über alle 5 Phase-0-Specs × {React, Angular} ist Folge-Phase.

## Workflow: Neue Referenz hinzufügen

1. Spec-Codegen lokal laufen lassen (mit Bedrock-Replay-Cache).
2. `PlaywrightPixelmatchDriver.render()` auf den Output anwenden, das
   resultierende `actual.png` als Referenz nach `specs/screenshots/<name>.png`
   committen.
3. Test in `core/tests/test_conformance_visual.py` ergänzen (analog
   `test_visual_regression_button_react`).

Siehe `docs/visual-regression.md` für Details.

## Fehlende PNGs

Wenn eine Referenz-PNG fehlt, skippt der Test sauber via
`pytest.skip("reference_missing: …")` — kein Failure.
