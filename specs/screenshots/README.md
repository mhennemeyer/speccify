# Referenz-Screenshots

Verzeichnis-Konvention für Visual-Regression (Phase 5c Skeleton → Phase 5d
Sweep). Siehe [`docs/visual-regression.md`](../../docs/visual-regression.md)
für die volle Doku.

## Namens-Konvention

Phase 5d nutzt eine **flache Namens-Konvention** (OQ1 = a):

```
specs/screenshots/<spec-name>-<target>.png
```

Beispiele:

- `button-react.png`, `button-angular.png`
- `contact-form-react.png`, `contact-form-angular.png`
- `login-screen-react.png`, `login-screen-angular.png`
- `onboarding-wizard-react.png`, `onboarding-wizard-angular.png`

`http-api-client` ist headless und **nicht** im Sweep (ZQ1).

Phase-5c-Skeleton-PNG `button-primary.png` (variant-basiert, target-agnostisch)
existiert ggf. zusätzlich — Phase-5d-Sweep ignoriert sie.

## Coverage

| Spec                | Targets              | PNGs |
| ------------------- | -------------------- | ---- |
| `button`            | react + angular      | 2    |
| `contact-form`      | react + angular      | 2    |
| `login-screen`      | react + angular      | 2    |
| `onboarding-wizard` | react + angular      | 2    |
| **Summe**           |                      | **8** |

## Workflow: PNGs (re-)generieren

```bash
# Alle 8 PNGs neu aufnehmen (idempotent, deterministisch):
uv run python scripts/record_visual_snapshots.py --all

# Nur eine Kombination:
uv run python scripts/record_visual_snapshots.py --spec button --target react
```

Voraussetzungen:

- `node` + `npm` (Node 20+).
- Einmaliger Playwright-Chromium-Install:
  `npx --yes playwright@1.44.0 install --with-deps chromium`
- Eingecheckte Replay-Cache-Fixtures unter `tests/fixtures/llm-cache/`
  (kein Netz nötig, Phase 5b).

Das Skript ruft denselben `PlaywrightPixelmatchDriver`, den der Sweep-Test
in CI nutzt (Single-Source-of-Truth, OQ3 = a).

## Fehlende PNGs

Wenn eine Referenz-PNG fehlt, skippt der Sweep-Test sauber mit
`pytest.skip("reference_missing: …")` — kein Failure. Die Maintainer-Hoheit
über die PNGs bleibt damit explizit (analog Phase-5b-Replay-Cache-Fixtures).
