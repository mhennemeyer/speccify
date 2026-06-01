"""Phase 5d Stage 3: Parametrisierter Visual-Regression-Sweep über alle UI-Specs.

Matrix: `4 UI-Specs × 2 Targets = 8 Tests` (`http-api-client` ist headless und
explizit nicht im Sweep, ZQ1). Jeder Test:

1. Lädt die Spec aus `registry-fixtures/` (neueste Version),
2. Rendert sie offline via Replay-Cache (`ReplayCacheClient` über
   `tests/fixtures/llm-cache/`),
3. Vergleicht das gerenderte Output gegen die committed Referenz-PNG unter
   `specs/screenshots/<spec-name>-<target>.png` via
   `VisualRegressionBackend` + `PlaywrightPixelmatchDriver`.

Skip-Strategie (OQ: dedizierte Reasons für CI-Sichtbarkeit):

- `toolchain_missing_node`: `node`/`npm` nicht im `$PATH`.
- `reference_missing`: Referenz-PNG existiert (noch) nicht (Maintainer-Hoheit
  via `scripts/record_visual_snapshots.py`).
- `toolchain_missing_chromium`: Playwright-Browser nicht installiert
  (`executable doesn't exist` / `playwright install`).

Default-Tolerance: 10 % (OQ7 = a, global, keine Per-Pfad-Overrides).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from speccify_core import (
    LocalRegistry,
    PlaywrightPixelmatchDriver,
    ReplayCache,
    ReplayCacheClient,
    VisualRegressionBackend,
    render_for_target,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_ROOT = REPO_ROOT / "registry-fixtures"
CACHE_DIR = REPO_ROOT / "tests" / "fixtures" / "llm-cache"
SCREENSHOTS_DIR = REPO_ROOT / "specs" / "screenshots"

# Phase-5d-Sweep-Matrix (siehe Plan-Stage-0-Audit). `http-api-client` ist
# headless und gehört nicht in den Sweep (ZQ1).
UI_SPECS: tuple[str, ...] = ("button", "contact-form", "login-screen", "onboarding-wizard")
TARGETS: tuple[str, ...] = ("react", "angular")
SCOPE: str = "org"

# Globaler Tolerance-Default (OQ7 = a). Pro-Pfad-Overrides wären ein
# Schema-Bump → vertagt auf eigene Phase.
DEFAULT_TOLERANCE: float = 0.10


def _reference_path(spec_name: str, target: str) -> Path:
    """Flache Namens-Konvention (OQ1 = a): `<spec-name>-<target>.png`."""
    return SCREENSHOTS_DIR / f"{spec_name}-{target}.png"


def _render_files(spec_name: str, target: str) -> dict[str, bytes]:
    """Rendert die Spec offline via Replay-Cache."""
    registry = LocalRegistry(FIXTURES_ROOT)
    spec_id = f"@{SCOPE}/{spec_name}"
    version = sorted(registry.list_versions(spec_id))[-1]
    spec = registry.fetch(spec_id, version)
    cache = ReplayCache(CACHE_DIR)
    rendered = render_for_target(spec, target, llm_client=ReplayCacheClient(cache=cache))
    return rendered.files


@pytest.mark.visual_regression
@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("spec_name", UI_SPECS)
def test_visual_regression_sweep(spec_name: str, target: str, tmp_path: Path) -> None:
    """8 Pfade: pixel-diff zwischen Codegen-Output und committed Referenz-PNG."""
    driver = PlaywrightPixelmatchDriver(target=target)
    if not driver.is_available():
        pytest.skip(f"toolchain_missing_node: {spec_name}/{target}")

    reference = _reference_path(spec_name, target)
    if not reference.exists():
        pytest.skip(
            f"reference_missing: {reference.relative_to(REPO_ROOT)} ist noch nicht "
            f"committed (Workflow: scripts/record_visual_snapshots.py --spec "
            f"{spec_name} --target {target})."
        )

    files = _render_files(spec_name, target)
    backend = VisualRegressionBackend(driver=driver, tolerance=DEFAULT_TOLERANCE)

    try:
        result = backend.compare(files=files, reference=reference, work_dir=tmp_path)
    except RuntimeError as exc:
        # Playwright-Browser fehlt lokal → kein Failure, sondern dedizierter
        # Skip-Reason (CI installiert Chromium explizit; lokal opt-in).
        msg = str(exc).lower()
        if "executable doesn't exist" in msg or "playwright install" in msg:
            pytest.skip(f"toolchain_missing_chromium: {spec_name}/{target}: {exc}")
        raise

    # Bei Failure: Diff-Image-Pfad in den Assert-Fehler einbetten, damit CI-
    # Artefakte direkt auffindbar sind.
    assert result.passed, (
        f"{spec_name}/{target}: pixel-diff {result.diff_ratio:.2%} überschreitet "
        f"Tolerance {result.tolerance:.0%}; diff_image={result.diff_image_path}"
    )
