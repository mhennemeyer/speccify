---
title: "Visual Regression (Phase 5d — Voller Sweep)"
description: "Visual-Regression-Stack: vergleicht generierten Component-Code mit committed Referenz-Screenshots via headless Chromium (Playwright) + Pixel-Diff (pixelmatch). **Phase 5d** erweitert das Phase-5c-Skeleton auf den vollen Sweep über **4 UI-Specs × {react, angular} = 8 Pfade**."
---

{/* AUTOGENERIERT aus docs/ via scripts/sync_docs_to_site.py — nicht von Hand editieren. */}

Visual-Regression-Stack: vergleicht generierten Component-Code mit committed
Referenz-Screenshots via headless Chromium (Playwright) + Pixel-Diff
(pixelmatch). **Phase 5d** erweitert das Phase-5c-Skeleton auf den vollen
Sweep über **4 UI-Specs × {react, angular} = 8 Pfade**.

Siehe auch: [`docs/conformance.md`](/conformance/) (Build-Smoke, Phase 5a)
und die archivierten Pläne
[`phase-5c-visual-regression-skeleton.md`](../.agent/plans/archive/phase-5c-visual-regression-skeleton.md)
und [`phase-5d-visual-regression-coverage.md`](../.agent/plans/archive/phase-5d-visual-regression-coverage.md).

## Coverage-Stand

| Phase | Pfade | Specs | Targets |
| ----- | ----- | ----- | ------- |
| 5c    | 1     | `button` (primary) | `react` |
| 5d    | **8** | `button`, `contact-form`, `login-screen`, `onboarding-wizard` (jeweils erster Screenshot) | `react`, `angular` |

`http-api-client` ist headless und nicht im Sweep (ZQ1). SwiftUI-Visual-
Regression bleibt eigener Phase (Xcode-UI-Tests).

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

Phase 5d nutzt eine **flache Namens-Konvention** (OQ1 = a) für den Sweep:

```
specs/screenshots/<spec-name>-<target>.png
```

Beispiele:

- `specs/screenshots/button-react.png`
- `specs/screenshots/button-angular.png`
- `specs/screenshots/contact-form-react.png`
- … (8 PNGs insgesamt)

Phase-5c-Variante (`button-primary.png` per Variante, target-agnostisch)
bleibt fürs Skeleton koexistent — der Sweep-Test in Phase 5d nutzt
ausschließlich das flache Schema oben.

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

## Recording-Workflow (Phase 5d)

Phase 5d liefert ein Maintainer-Tool, das alle 8 Sweep-PNGs deterministisch
regeneriert — kein händisches Driver-Aufrufen mehr nötig:

```bash
# Alle 8 PNGs neu erzeugen (idempotent — zweimal in Folge → byte-identisch):
uv run python scripts/record_visual_snapshots.py --all

# Nur eine einzelne Kombination:
uv run python scripts/record_visual_snapshots.py --spec button --target react

# In ein alternatives Output-Verzeichnis schreiben (für Diff-Review):
uv run python scripts/record_visual_snapshots.py --all --out /tmp/snaps
```

Das Skript:

1. Lädt die Spec aus `registry-fixtures/<scope>/<name>/<version>/`
   (neueste Version).
2. Rendert sie **offline** via `ReplayCacheClient` über die committed
   Replay-Cache-Fixtures unter `tests/fixtures/llm-cache/` (kein Netz nötig).
3. Ruft `PlaywrightPixelmatchDriver.render()` direkt auf (Single-Source-of-
   Truth, OQ3 = a — derselbe Driver, den der Sweep-Test nutzt).
4. Schreibt die PNG nach `specs/screenshots/<spec-name>-<target>.png`.

Voraussetzungen analog Sweep-Test: `node`/`npm` + einmaliger
`npx playwright install chromium`.

### Neue UI-Spec hinzufügen

1. Spec nach `registry-fixtures/<scope>/<name>/<version>/spec.speccify.yaml`
   committen + Replay-Cache via `scripts/record_llm_cache.py --target all`
   füllen.
2. Spec-Namen in `UI_SPECS` von `scripts/record_visual_snapshots.py` und
   `core/tests/test_visual_regression_sweep.py` ergänzen.
3. `uv run python scripts/record_visual_snapshots.py --spec <name> --target react`
   + Analog für Angular → PNGs reviewen + committen.

## CI-Verhalten

Eigener Workflow [`.github/workflows/visual-regression.yml`](../.github/workflows/visual-regression.yml):

- **Trigger**: Push/PR mit Änderungen an `conformance_visual.py`,
  `test_conformance_visual.py`, `specs/screenshots/**` oder dem Workflow
  selbst — plus Nightly-Cron (`17 4 * * *`) + `workflow_dispatch`.
- **Job**: `visual-regression-sweep` auf Ubuntu-latest, Node 20, Playwright-
  Chromium gecached unter `~/.cache/ms-playwright`. **Ein** Job für alle
  8 Pfade (OQ5 = a) — npm install + Chromium-Install nur einmal.
- Bei Failure: Upload der `actual.png`/`diff.png`-Artefakte aus dem Pytest-
  Tmp-Dir (Retention 14 Tage), damit Maintainer ohne lokales Setup reviewen
  können.
- **Default-CI (`ci.yml`)** bleibt unverändert — Marker-Exclude schützt vor
  Browser-Downloads im Standard-Pfad.

## Toolchain-Fehler → Skip, nicht Failure

Analog Phase 5a: der Sweep-Test mappt drei verschiedene Fehlerklassen auf
dedizierte Skip-Reasons (für CI-Sichtbarkeit):

| Skip-Reason                  | Ursache                                              |
| ---------------------------- | ---------------------------------------------------- |
| `toolchain_missing_node`     | `node`/`npm` nicht im `$PATH`                        |
| `toolchain_missing_chromium` | Playwright-Browser nicht installiert                 |
| `reference_missing`          | Referenz-PNG (`specs/screenshots/<spec>-<target>.png`) noch nicht committed |

Kein Fehlerpfad löst ein Failure aus — die Maintainer-Hoheit über die
Referenz-PNGs bleibt explizit (analog Phase-5b-Replay-Cache-Fixtures).

## Troubleshooting: Determinismus

Visual-Regression ist notorisch zickig bei Font-Rendering und OS-Drift.
Phase 5d zieht **mittlere Determinismus-Härte** (OQ4 = b):

- **Viewport** fest gepinnt auf 320 × 240 px (`PlaywrightPixelmatchDriver`).
- `prefers-reduced-motion: reduce` via Playwright-Context (`reducedMotion`)
  + CSS-`animation-duration: 0s !important` als Belt-and-Suspenders.
- `prefers-color-scheme: light` via Playwright-Context (`colorScheme`) +
  `<meta name="color-scheme" content="light">` + harte Farb-Pins
  (`#fff` Background, `#000` Text) — kein OS-Dark-Mode-Drift.
- `forcedColors: 'none'` schützt vor OS-Accessibility-High-Contrast-Themes.
- Font-Stack `'Courier New', Courier, monospace` mit
  `-webkit-font-smoothing: none` — System-Default-Font-Drift zwischen
  macOS und Linux-CI ist die häufigste Failure-Quelle.

Wenn der Sweep trotzdem lokal grün, aber in CI rot wird:

1. Diff-PNG aus den CI-Artefakten ziehen (`visual-regression-diffs-<run-id>`)
   und visuell prüfen — meistens ist es Anti-Aliasing am Font-Rand.
2. Tolerance global hochziehen (`DEFAULT_TOLERANCE` in
   `core/tests/test_visual_regression_sweep.py`).
3. PNG lokal **auf einem Linux-Container** neu aufnehmen, damit die Referenz
   zum CI-Renderer passt (z. B. via `docker run -v $PWD:/repo ...`).

## Nicht-Ziele dieser Phase

- **Schema-Bump** `screenshots[].tolerance` (eigene Schema-Phase, vertagt).
- **`--update-snapshots`-Pytest-Flag** (OQ6 vertagt; Recorder-Script reicht).
- **Mehrere Screenshots pro Spec** — Phase 5d deckt nur den ersten
  Screenshot pro UI-Spec; weitere Varianten (`button-loading`, `error`,
  `step2`, …) bleiben Folge-Phase.
- **SwiftUI-Visual-Regression** (braucht Xcode-UI-Test-Harness, macOS-only).
- **Echter Component-Mount** mit React/Angular-Runtime — Phase 5d nutzt
  weiterhin die Phase-5c-`<pre>`-Sandbox (screenshottet den generierten
  Code, nicht den gemounteten Component). Echter Renderer ist eigener
  Phasen-Kandidat (Webpack/Vite-Pipeline, AOT-Angular).
