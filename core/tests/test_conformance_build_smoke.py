"""Tests für `speccify_core.conformance_build_smoke` (Phase 5a Stage 1 — React).

Die echten Toolchain-Tests sind mit `@pytest.mark.conformance` markiert; der
Default-Pytest-Lauf (`-m "not conformance"` via `pyproject.toml`) führt sie
nicht aus. Opt-in: `uv run pytest -m conformance` oder
`uv run pytest core/tests/test_conformance_build_smoke.py -m conformance`.

Reine Unit-Tests des Backends (ohne externe Toolchain) laufen *immer* mit,
über einen `FakeDriver`, der das `ToolchainDriver`-Protocol erfüllt.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from speccify_core import (
    BUILD_SMOKE_TOOLCHAIN_MISSING,
    AngularToolchainDriver,
    BuildSmokeBackend,
    GeneratedFile,
    LlmGeneratorPin,
    LockEntry,
    Lockfile,
    ReactToolchainDriver,
    ReplayCache,
    ReplayCacheClient,
    SwiftUIToolchainDriver,
    ToolchainDriver,
    build_smoke_driver_for,
    render_for_target,
)
from speccify_core.codegen import react_llm
from speccify_core.registry import LocalRegistry, Version

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_FIXTURES = REPO_ROOT / "registry-fixtures"
CACHE_DIR = REPO_ROOT / "tests" / "fixtures" / "llm-cache"


# --- Fixtures / Helpers -------------------------------------------------------


def _client() -> ReplayCacheClient:
    return ReplayCacheClient(cache=ReplayCache(CACHE_DIR), offline=True)


def _render_button() -> tuple[dict[str, bytes], object]:
    registry = LocalRegistry(REGISTRY_FIXTURES)
    spec = registry.fetch("@org/button", Version.parse("0.1.0"))
    rendered = render_for_target(spec, "react", llm_client=_client())
    return rendered.files, rendered.cache_key


def _button_entry(files: dict[str, bytes], cache_key: object) -> LockEntry:
    gen_files = tuple(
        GeneratedFile(path=p, sha256=f"sha256:{hashlib.sha256(b).hexdigest()}")
        for p, b in files.items()
    )
    return LockEntry(
        id="@org/button",
        version="0.1.0",
        sha256="sha256:" + "0" * 64,
        resolved_via="registry-fixtures",
        target="react",
        generator=LlmGeneratorPin(
            provider=react_llm.PROVIDER,
            model=react_llm.MODEL,
            prompt_version=react_llm.PROMPT_VERSION,
            cache_key=f"sha256:{cache_key.digest()}",  # type: ignore[attr-defined]
            seed=react_llm.DEFAULT_SEED,
        ),
        generated_files_sha256=gen_files,
    )


@dataclass
class _FakeDriver:
    """`ToolchainDriver`-Stub für plattformunabhängige Unit-Tests."""

    target: str = "react"
    available: bool = True
    returncode: int = 0
    output: str = ""
    received_files: dict[str, bytes] = field(default_factory=dict)

    def is_available(self) -> bool:
        return self.available

    def build(self, *, files: dict[str, bytes], work_dir: Path) -> tuple[int, str]:
        self.received_files = dict(files)
        return self.returncode, self.output


# --- Unit-Tests (immer aktiv) -------------------------------------------------


def test_factory_returns_react_driver_for_react() -> None:
    driver = build_smoke_driver_for("react")
    assert isinstance(driver, ReactToolchainDriver)
    assert driver.target == "react"


def test_factory_returns_none_for_unknown_target() -> None:
    assert build_smoke_driver_for("kotlin") is None
    assert build_smoke_driver_for("flutter") is None


def test_factory_returns_angular_driver_for_angular() -> None:
    driver = build_smoke_driver_for("angular")
    assert isinstance(driver, AngularToolchainDriver)
    assert driver.target == "angular"


def test_factory_returns_swiftui_driver_for_swiftui() -> None:
    driver = build_smoke_driver_for("swiftui")
    assert isinstance(driver, SwiftUIToolchainDriver)
    assert driver.target == "swiftui"


def test_backend_reports_toolchain_missing_for_unknown_target() -> None:
    files, key = _render_button()
    entry = _button_entry(files, key)
    other = LockEntry(
        id=entry.id,
        version=entry.version,
        sha256=entry.sha256,
        resolved_via=entry.resolved_via,
        target="kotlin",  # nicht im Default-Driver-Set
        generator=entry.generator,
        generated_files_sha256=entry.generated_files_sha256,
    )
    backend = BuildSmokeBackend()
    report = backend.run(
        lockfile=Lockfile(targets=("kotlin",), entries=(other,)),
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
    )
    assert len(report.results) == 1
    result = report.results[0]
    assert result.status == BUILD_SMOKE_TOOLCHAIN_MISSING
    assert "kotlin" in result.messages[0]


def test_backend_reports_toolchain_missing_when_driver_unavailable() -> None:
    files, key = _render_button()
    fake = _FakeDriver(target="react", available=False)
    backend = BuildSmokeBackend(drivers={"react": fake})
    report = backend.run(
        lockfile=Lockfile(targets=("react",), entries=(_button_entry(files, key),)),
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
    )
    assert report.results[0].status == BUILD_SMOKE_TOOLCHAIN_MISSING


def test_backend_passes_rendered_files_to_driver_and_reports_ok() -> None:
    files, key = _render_button()
    fake = _FakeDriver(target="react", available=True, returncode=0)
    backend = BuildSmokeBackend(drivers={"react": fake})
    report = backend.run(
        lockfile=Lockfile(targets=("react",), entries=(_button_entry(files, key),)),
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
    )
    assert report.ok
    assert report.backend == "build-smoke"
    # Driver hat die gerenderten Files erhalten (gleiche Pfade, gleiche Bytes).
    assert set(fake.received_files.keys()) == set(files.keys())
    for path, blob in files.items():
        assert fake.received_files[path] == blob


def test_backend_reports_build_failed_with_truncated_output() -> None:
    files, key = _render_button()
    fake = _FakeDriver(
        target="react",
        available=True,
        returncode=2,
        output="x" * 5000,  # > 2000 zur Trunc-Probe
    )
    backend = BuildSmokeBackend(drivers={"react": fake})
    report = backend.run(
        lockfile=Lockfile(targets=("react",), entries=(_button_entry(files, key),)),
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
    )
    result = report.results[0]
    assert result.status == "build_failed"
    assert "returncode=2" in result.messages[0]
    # Snippet abgeschnitten + Truncation-Marker
    assert "…(truncated)" in result.messages[1]
    assert len(result.messages[1]) < 5000


def test_backend_target_filter_skips_nonmatching_entries() -> None:
    files, key = _render_button()
    fake = _FakeDriver(target="react", available=True, returncode=0)
    backend = BuildSmokeBackend(drivers={"react": fake})
    report = backend.run(
        lockfile=Lockfile(targets=("react",), entries=(_button_entry(files, key),)),
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
        targets=("swiftui",),  # passt nicht → leeres Result
    )
    assert report.results == ()


def test_react_driver_is_available_when_npm_present() -> None:
    driver = ReactToolchainDriver()
    expected = shutil.which("npm") is not None and shutil.which("node") is not None
    assert driver.is_available() is expected


def test_angular_driver_is_available_when_npm_present() -> None:
    driver = AngularToolchainDriver()
    expected = shutil.which("npm") is not None and shutil.which("node") is not None
    assert driver.is_available() is expected


def test_swiftui_driver_is_available_when_swiftc_and_xcrun_present() -> None:
    driver = SwiftUIToolchainDriver()
    expected = shutil.which("swiftc") is not None and shutil.which("xcrun") is not None
    assert driver.is_available() is expected


# --- Marker-Compliance-Check --------------------------------------------------


def test_toolchain_driver_protocol_structure() -> None:
    """Stelle sicher, dass `ToolchainDriver` ein laufzeit-checkbares Protocol bleibt."""
    driver: ToolchainDriver = ReactToolchainDriver()
    # Statische Attribut-Erwartung — kein runtime-isinstance, da `Protocol` ohne
    # `@runtime_checkable` deklariert ist (bewusst, vermeidet Magic).
    assert driver.target == "react"
    assert hasattr(driver, "is_available")
    assert hasattr(driver, "build")


# --- Conformance-Test (Opt-in via `pytest -m conformance`) --------------------


@pytest.mark.conformance
def test_react_build_smoke_button_via_tsc() -> None:
    """End-to-end Build-Smoke: gerenderter Button-TSX muss durch `tsc --noEmit` gehen.

    Skipped, wenn `npx`/`node` nicht verfügbar sind (z. B. minimaler CI-Container).
    """
    driver = ReactToolchainDriver()
    if not driver.is_available():
        pytest.skip("npm/node not available — toolchain missing.")

    files, key = _render_button()
    backend = BuildSmokeBackend()  # Default-Drivers (React aktiv)
    report = backend.run(
        lockfile=Lockfile(targets=("react",), entries=(_button_entry(files, key),)),
        registry=LocalRegistry(REGISTRY_FIXTURES),
        llm_client=_client(),
    )
    assert report.ok, [r.messages for r in report.failures()]
    assert report.results[0].status == "ok"
    assert report.results[0].target == "react"


# Synthetische Mini-Sources für die Angular/SwiftUI-End-to-End-Tests. Phase 5a
# verifiziert den Toolchain-Pfad selbst; vollständige Spec×Target-Cache-
# Befüllung ist Phase-5b-Scope (vgl. Plan-OQ5). Die Snippets sind bewusst
# minimal, decken aber die kritischen Konstrukte ab, die der Codegen produziert
# (Angular `@Component`-Decorator + signal-API; SwiftUI `View`-Conformance).

_SYNTHETIC_ANGULAR_COMPONENT = b"""\
import { Component } from '@angular/core';

@Component({
  selector: 'org-button',
  standalone: true,
  template: `<button (click)="onClick()">{{ label }}</button>`,
})
export class ButtonComponent {
  label: string = 'Click me';

  onClick(): void {
    // Build-Smoke: nur Typcheck, keine Runtime.
  }
}
"""

_SYNTHETIC_SWIFTUI_VIEW = b"""\
import SwiftUI

struct Button: View {
    let label: String

    var body: some View {
        SwiftUI.Button(action: {}) {
            Text(label)
        }
    }
}
"""


@pytest.mark.conformance
def test_angular_build_smoke_synthetic_via_tsc(tmp_path: Path) -> None:
    """End-to-end Build-Smoke für Angular: synthetischer `@Component`-Snippet
    muss durch `tsc --noEmit` mit den gepinnten Angular-Typings gehen.

    Phase-5a-Scope: prüft den Driver-Pfad selbst (npm install + lokales tsc).
    Cross-Spec×Cache-Coverage kommt in Phase 5b.
    """
    driver = AngularToolchainDriver()
    if not driver.is_available():
        pytest.skip("npm/node not available — toolchain missing.")

    files = {"org/button.component.ts": _SYNTHETIC_ANGULAR_COMPONENT}
    returncode, output = driver.build(files=files, work_dir=tmp_path)
    assert returncode == 0, f"Angular-Build-Smoke fehlgeschlagen:\n{output}"


@pytest.mark.conformance
def test_swiftui_build_smoke_synthetic_via_swiftc(tmp_path: Path) -> None:
    """End-to-end Build-Smoke für SwiftUI: synthetischer `View`-Snippet muss
    durch `swiftc -typecheck` gegen das macOS-SDK gehen.

    Skipped auf Linux-CI (kein `xcrun`/SwiftUI-Framework verfügbar).
    """
    driver = SwiftUIToolchainDriver()
    if not driver.is_available():
        pytest.skip("swiftc/xcrun not available — toolchain missing.")

    files = {"org/Button.swift": _SYNTHETIC_SWIFTUI_VIEW}
    returncode, output = driver.build(files=files, work_dir=tmp_path)
    assert returncode == 0, f"SwiftUI-Build-Smoke fehlgeschlagen:\n{output}"
