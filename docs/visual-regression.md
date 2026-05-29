# Visual Regression (Phase 5c Skeleton)

Visual-Regression-Skeleton zum Conformance-Stack: vergleicht generierten
Component-Code mit committed Referenz-Screenshots via headless Chromium
(Playwright) + Pixel-Diff (pixelmatch).

Siehe auch: [`docs/conformance.md`](./conformance.md) (Build-Smoke, Phase 5a)
und der archivierte Plan
[`.agent/plans/archive/phase-5c-visual-regression-skeleton.md`](../.agent/plans/archive/phase-5c-visual-regression-skeleton.md).

## Konzept

Specs beschreiben Komponenten u. a. mit `screenshots:`-Referenzen
(z. B. `./screenshots/button-primary.png`). Phase 5c liefert die
**Infrastruktur**, um diese Referenzen automatisiert zu prüfen:

```
spec.yaml + screenshots/
        ↓
   Codegen-Pipeline
        ↓
   Generated Code  ───► VisualDiffDriver (Playwright headless)
                          ↓
                       actual.png
                          ↓
   Referenz-PNG   ───► VisualRegressionBackend (pixelmatch)
                          ↓
                     VisualDiffResult
                          ↓
                  pytest -m visual_regression
```

Skeleton-Scope (Stage-0-Entscheidungen):

- **1 Driver**: `PlaywrightPixelmatchDriver` für React + Angular (`visual_driver_for(target)`).
- **1 Referenz-PNG** im Repo (Button × React) als End-to-End-Proof.
- **Default-Tolerance**: 10 % Pixel-Diff (`DEFAULT_VISUAL_TOLERANCE = 0.1`),
  hardcoded — kein Schema-Bump für `screenshots[].tolerance` in dieser Phase.
- **SwiftUI ist Out-of-Scope**: kein Headless-Renderer ohne Xcode-UI-Test-Setup.
- **`--update-snapshots` Out-of-Scope**: manuelles Überschreiben der PNG genügt
  im Skeleton; Folge-Phase erweitert das.

## Verzeichnis-Konvention

Referenz-PNGs liegen unter `specs/screenshots/<spec-slug>-<variant>.png`,
matched mit dem `screenshots:`-Feld der jeweiligen Spec (relative Pfade
ausgehend vom Spec-Manifest, z. B. `./screenshots/button-primary.png`).

## Lokales Setup

Voraussetzungen:

- `node` + `npm` (Node 20+).
- Playwright-Browser einmalig installieren:

```bash
npx --yes playwright@1.44.0 install --with-deps chromium
```

Visual-Regression-Tests laufen:

```bash
uv run pytest -m visual_regression
```

Im Default-Pytest-Lauf sind die Tests via
`addopts = -m "not conformance and not visual_regression"` (in `pyproject.toml`)
ausgeschlossen — sie sind opt-in, analog dem Build-Smoke-Marker (Phase 5a).

## Backend-API

```python
from pathlib import Path
from speccify_core import (
    PlaywrightPixelmatchDriver,
    VisualRegressionBackend,
    visual_driver_for,
)

driver = visual_driver_for("react")  # PlaywrightPixelmatchDriver
backend = VisualRegressionBackend(driver=driver)  # tolerance=0.1 default

result = backend.compare(
    files={"src/Button.tsx": b"…generated…"},
    reference=Path("specs/screenshots/button-primary.png"),
    work_dir=Path("/tmp/vr-work"),
)

assert result.passed
print(result.diff_ratio, result.pixel_diff_count, result.diff_image_path)
```

`VisualDiffResult`-Felder:

| Feld                 | Typ           | Bedeutung                                      |
| -------------------- | ------------- | ---------------------------------------------- |
| `passed`             | `bool`        | `diff_ratio <= tolerance`                      |
| `pixel_diff_count`   | `int`         | Anzahl unterschiedlicher Pixel                 |
| `total_pixels`       | `int`         | Gesamtpixel des Vergleichs                     |
| `diff_ratio`         | `float`       | `pixel_diff_count / total_pixels`              |
| `tolerance`          | `float`       | aktive Tolerance (Default 0.1)                 |
| `diff_image_path`    | `Path \| None` | Pfad zum erzeugten Diff-PNG (für Debug)        |
| `reason`             | `str \| None`  | `'toolchain_missing'` / `'tolerance_exceeded'` |
| `toolchain_missing`  | Property      | `reason == 'toolchain_missing'`                |

## Workflow: Neue Referenz hinzufügen

1. Spec-Codegen lokal mit Bedrock-Replay-Cache laufen lassen (analog
   Phase-5a-Build-Smoke-Workflow).
2. `PlaywrightPixelmatchDriver.render(files=…, work_dir=tmp)` aufrufen, das
   erzeugte `actual.png` prüfen und nach `specs/screenshots/<name>.png`
   committen.
3. Test in `core/tests/test_conformance_visual.py` ergänzen (Vorbild:
   `test_visual_regression_button_react`).
4. CI prüft die neuen PNGs automatisch via Path-Filter im
   `visual-regression.yml`-Workflow.

## CI-Verhalten

Eigener Workflow [`.github/workflows/visual-regression.yml`](../.github/workflows/visual-regression.yml):

- **Trigger**: Push/PR mit Änderungen an `conformance_visual.py`,
  `test_conformance_visual.py`, `specs/screenshots/**` oder dem Workflow
  selbst — plus Nightly-Cron (`17 4 * * *`) + `workflow_dispatch`.
- **Job**: `visual-regression-react` auf Ubuntu-latest, Node 20, Playwright-
  Chromium gecached unter `~/.cache/ms-playwright`.
- **Default-CI (`ci.yml`)** bleibt unverändert — Marker-Exclude schützt vor
  Browser-Downloads im Standard-Pfad.

## Toolchain-Fehler → Skip, nicht Failure

Analog Phase 5a: `driver.is_available()` prüft `node`+`npm`; wenn die
Playwright-Browser fehlen, fängt der E2E-Test die `RuntimeError`-Meldungen
mit `"executable doesn't exist"` ab und mappt sie auf `pytest.skip(...)`.
Fehlende Referenz-PNG → ebenfalls Skip (`reason="reference_missing: …"`).

## Nicht-Ziele dieser Phase

- Voller Sweep über alle Specs × Targets (Folge-Phase).
- Schema-Bump `screenshots[].tolerance` (eigene Schema-Phase).
- `--update-snapshots`-Pytest-Flag (Folge-Phase mit vollem Sweep).
- SwiftUI-Visual-Regression (braucht Xcode-UI-Test-Harness).
- Echter Component-Mount mit React/Angular-Runtime — Skeleton screenshottet
  eine Code-Sandbox (`<pre>`-Render der Files), nicht den Live-Component.
  Ein echter Renderer ist Folge-Phase.
