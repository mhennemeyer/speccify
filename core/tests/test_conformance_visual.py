"""Tests für `speccify_core.conformance_visual` (Phase 5c Skeleton).

Unit-Tests (Backend-Logik via Fake-Driver) laufen *immer* — sie brauchen
weder Node noch Playwright. Der echte End-to-End-Test mit Playwright +
pixelmatch ist mit `@pytest.mark.visual_regression` markiert und im
Default-Pytest-Lauf via `-m "not conformance and not visual_regression"`
(siehe `pyproject.toml`) ausgeschlossen.

Opt-in:

    uv run pytest -m visual_regression
    uv run pytest core/tests/test_conformance_visual.py -m visual_regression
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from speccify_core import (
    DEFAULT_VISUAL_TOLERANCE,
    VISUAL_TOOLCHAIN_MISSING,
    PlaywrightPixelmatchDriver,
    VisualDiffDriver,
    VisualDiffResult,
    VisualRegressionBackend,
    visual_driver_for,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PNG = REPO_ROOT / "specs" / "screenshots" / "button-primary.png"


# --- Fake-Driver für Unit-Tests ----------------------------------------------


@dataclass
class _FakeDriver:
    """Erfüllt das `VisualDiffDriver`-Protocol ohne echte Toolchain."""

    target: str = "react"
    available: bool = True
    diff_pixels: int = 0
    total_pixels: int = 1000
    render_calls: list[dict[str, bytes]] = field(default_factory=list)
    diff_calls: list[tuple[Path, Path]] = field(default_factory=list)

    def is_available(self) -> bool:
        return self.available

    def render(self, *, files: dict[str, bytes], work_dir: Path) -> Path:
        self.render_calls.append(dict(files))
        actual = work_dir / "actual.png"
        actual.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        return actual

    def diff(self, *, expected: Path, actual: Path, work_dir: Path) -> tuple[int, int, Path | None]:
        self.diff_calls.append((expected, actual))
        diff_path = work_dir / "diff.png"
        diff_path.write_bytes(b"\x89PNG\r\n\x1a\nfake-diff")
        return self.diff_pixels, self.total_pixels, diff_path


# --- Factory / Protocol -------------------------------------------------------


def test_factory_returns_driver_for_react() -> None:
    driver = visual_driver_for("react")
    assert isinstance(driver, PlaywrightPixelmatchDriver)
    assert driver.target == "react"


def test_factory_returns_driver_for_angular() -> None:
    driver = visual_driver_for("angular")
    assert isinstance(driver, PlaywrightPixelmatchDriver)
    assert driver.target == "angular"


def test_factory_returns_none_for_swiftui() -> None:
    # Phase 5c Skeleton: SwiftUI hat keinen Visual-Driver (kein Headless-Renderer
    # ohne Xcode-UI-Test-Setup). Folge-Phase.
    assert visual_driver_for("swiftui") is None


def test_factory_returns_none_for_unknown_target() -> None:
    assert visual_driver_for("flutter") is None


def test_visual_diff_driver_protocol_structure() -> None:
    # Strukturelle Prüfung: Protocol verlangt `target`, `is_available`,
    # `render`, `diff`. `_FakeDriver` muss als `VisualDiffDriver`
    # akzeptiert werden (statisch + zur Laufzeit via duck typing).
    fake: VisualDiffDriver = _FakeDriver()
    assert fake.target == "react"
    assert fake.is_available() is True


# --- Backend-Logik -----------------------------------------------------------


def test_backend_reports_toolchain_missing_when_driver_unavailable(tmp_path: Path) -> None:
    fake = _FakeDriver(available=False)
    backend = VisualRegressionBackend(driver=fake)
    result = backend.compare(files={}, reference=tmp_path / "ref.png", work_dir=tmp_path)
    assert result.toolchain_missing is True
    assert result.reason == VISUAL_TOOLCHAIN_MISSING
    assert result.passed is False
    # Wenn die Toolchain fehlt, darf weder gerendert noch gediffed werden.
    assert fake.render_calls == []
    assert fake.diff_calls == []


def test_backend_reports_reference_missing(tmp_path: Path) -> None:
    fake = _FakeDriver()
    backend = VisualRegressionBackend(driver=fake)
    missing_ref = tmp_path / "does-not-exist.png"
    result = backend.compare(files={}, reference=missing_ref, work_dir=tmp_path)
    assert result.passed is False
    assert result.reason is not None
    assert result.reason.startswith("reference_missing")
    assert fake.render_calls == []


def test_backend_passes_when_diff_below_tolerance(tmp_path: Path) -> None:
    reference = tmp_path / "ref.png"
    reference.write_bytes(b"\x89PNG\r\n\x1a\nfake-ref")
    fake = _FakeDriver(diff_pixels=50, total_pixels=1000)  # 5 % Diff
    backend = VisualRegressionBackend(driver=fake)  # Default-Tolerance 10 %
    result = backend.compare(
        files={"src/Button.tsx": b"export const Button = () => null;\n"},
        reference=reference,
        work_dir=tmp_path,
    )
    assert result.passed is True
    assert result.reason is None
    assert result.pixel_diff_count == 50
    assert result.total_pixels == 1000
    assert result.diff_ratio == pytest.approx(0.05)
    assert result.tolerance == DEFAULT_VISUAL_TOLERANCE
    assert len(fake.render_calls) == 1
    assert len(fake.diff_calls) == 1


def test_backend_fails_when_diff_exceeds_tolerance(tmp_path: Path) -> None:
    reference = tmp_path / "ref.png"
    reference.write_bytes(b"\x89PNG\r\n\x1a\nfake-ref")
    fake = _FakeDriver(diff_pixels=250, total_pixels=1000)  # 25 % Diff
    backend = VisualRegressionBackend(driver=fake, tolerance=0.1)
    result = backend.compare(
        files={"src/Button.tsx": b"export const Button = () => null;\n"},
        reference=reference,
        work_dir=tmp_path,
    )
    assert result.passed is False
    assert result.reason == "tolerance_exceeded"
    assert result.diff_ratio == pytest.approx(0.25)


def test_backend_custom_tolerance_applied(tmp_path: Path) -> None:
    reference = tmp_path / "ref.png"
    reference.write_bytes(b"\x89PNG\r\n\x1a\nfake-ref")
    # 8 % Diff: bei Tolerance 0.05 fail, bei 0.1 pass.
    fake_strict = _FakeDriver(diff_pixels=80, total_pixels=1000)
    strict = VisualRegressionBackend(driver=fake_strict, tolerance=0.05)
    assert strict.compare(files={}, reference=reference, work_dir=tmp_path).passed is False

    fake_loose = _FakeDriver(diff_pixels=80, total_pixels=1000)
    loose = VisualRegressionBackend(driver=fake_loose, tolerance=0.10)
    assert loose.compare(files={}, reference=reference, work_dir=tmp_path).passed is True


def test_backend_handles_zero_total_pixels(tmp_path: Path) -> None:
    # Edge-Case: leere Bilder (sollte nicht passieren, aber Backend muss
    # robust sein → ZeroDivisionError-Schutz).
    reference = tmp_path / "ref.png"
    reference.write_bytes(b"\x89PNG")
    fake = _FakeDriver(diff_pixels=0, total_pixels=0)
    backend = VisualRegressionBackend(driver=fake)
    result = backend.compare(files={}, reference=reference, work_dir=tmp_path)
    assert result.passed is True  # 0 diff ≤ tolerance
    assert result.diff_ratio == 0.0


def test_visual_diff_result_toolchain_missing_property() -> None:
    missing = VisualDiffResult(
        passed=False,
        pixel_diff_count=0,
        total_pixels=0,
        diff_ratio=0.0,
        tolerance=DEFAULT_VISUAL_TOLERANCE,
        reason=VISUAL_TOOLCHAIN_MISSING,
    )
    assert missing.toolchain_missing is True

    ok = VisualDiffResult(
        passed=True,
        pixel_diff_count=0,
        total_pixels=1000,
        diff_ratio=0.0,
        tolerance=DEFAULT_VISUAL_TOLERANCE,
    )
    assert ok.toolchain_missing is False


# --- Echter Driver: Verfügbarkeits-Probe (kein Spawn) ------------------------


def test_playwright_driver_is_available_when_node_present() -> None:
    driver = PlaywrightPixelmatchDriver()
    expected = shutil.which("npm") is not None and shutil.which("node") is not None
    assert driver.is_available() is expected


# --- E2E: visual_regression-Marker, Opt-in ----------------------------------


@pytest.mark.visual_regression
def test_visual_regression_button_react(tmp_path: Path) -> None:
    """End-to-End-Proof: Button-React-Output vs. committed Referenz-PNG.

    Skip-Strategie analog Phase 5a:
    - Kein Node/npm → skip.
    - Kein `PLAYWRIGHT_BROWSERS_PATH` / kein Chromium-Install → der Backend
      würde an `RuntimeError` scheitern; um die Reibung im Skeleton klein
      zu halten, prüfen wir `driver.is_available()` und das Vorhandensein
      der Referenz-PNG, dann führen wir die Pipeline aus. Bei Fehlern in
      der Render-Pipeline (z. B. fehlende Browser) skippen wir.
    """
    driver = PlaywrightPixelmatchDriver(target="react")
    if not driver.is_available():
        pytest.skip("toolchain_missing: node/npm nicht verfügbar")
    if not REFERENCE_PNG.exists():
        pytest.skip(
            f"reference_missing: {REFERENCE_PNG} ist noch nicht committed "
            "(Folge-Substage: Snapshot via Maintainer-Workflow erzeugen)."
        )

    backend = VisualRegressionBackend(driver=driver)
    # Minimaler Button-React-Snippet als Stand-in für gerendertes Codegen-
    # Ergebnis (Phase-5c-Scope = Driver-Pfad). Cross-Spec×Cache-Coverage
    # bleibt Folge-Phase analog Phase-5a-Logik.
    files = {
        "src/Button.tsx": (
            b"export const Button = ({ label }: { label: string }) => <button>{label}</button>;\n"
        ),
    }
    try:
        result = backend.compare(files=files, reference=REFERENCE_PNG, work_dir=tmp_path)
    except RuntimeError as exc:
        # Playwright-Browser fehlen lokal → kein Failure, sondern Skip.
        msg = str(exc).lower()
        if "executable doesn't exist" in msg or "playwright install" in msg:
            pytest.skip(f"toolchain_missing: {exc}")
        raise

    # Skeleton-Assertion: Der Pipeline-Pfad liefert ein strukturiertes Result;
    # wir asserten *nicht* `passed=True`, weil die Referenz-PNG-Pflege
    # Maintainer-Hoheit ist. Wichtig ist, dass der Diff zahlenmäßig
    # funktioniert hat.
    assert result.total_pixels > 0
    assert result.tolerance == DEFAULT_VISUAL_TOLERANCE
