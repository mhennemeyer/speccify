"""Visual-Regression-Backend (Phase 5c Skeleton).

Liefert die Infrastruktur — Backend + `VisualDiffDriver`-Protocol + Result-
Dataclass — für Pixel-Diff-basierte Visual-Regression-Checks gegen committed
Referenz-Screenshots (z. B. `specs/screenshots/button-primary.png`).

Scope-Disziplin analog Phase 5a:

- Driver-Pfad zuerst, voller Sweep über alle Specs × Targets ist Folge-Phase.
- Mindestens ein konkreter Driver (`PlaywrightPixelmatchDriver`) für React +
  Angular über headless Chromium + `pixelmatch`-CLI.
- Fehlt die Toolchain (kein `node`/keine Playwright-Browser), liefert der
  Backend einen Result mit `reason="toolchain_missing"` — *kein* Failure,
  Tests skippen sauber (`pytest.skip(...)`).
- Default-Tolerance (Stage-0-OQ4) hardcoded auf 10 % Pixel-Diff; ein Schema-
  Bump für `screenshots[].tolerance` ist explizit *nicht* Teil dieser Phase.

Im Gegensatz zum Build-Smoke-Backend (das auf Lockfile-Einträgen arbeitet)
operiert dieser Backend bewusst auf der Ebene `(generated_code, reference_png)`:
Die Phase-5c-Aufgabe ist „Pixel-Diff funktioniert", nicht „integriert in den
vollen Conformance-Run". Der Schritt zu einem `ConformanceBackend`-Adapter
ist eine Folge-Substage.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

__all__ = [
    "VISUAL_TOOLCHAIN_MISSING",
    "DEFAULT_VISUAL_TOLERANCE",
    "VisualDiffResult",
    "VisualDiffDriver",
    "VisualRegressionBackend",
    "PlaywrightPixelmatchDriver",
    "visual_driver_for",
]

# Sentinel-`reason` analog `BUILD_SMOKE_TOOLCHAIN_MISSING` (Phase 5a). Tests
# sollen diesen Wert zu `pytest.skip("toolchain_missing")` mappen.
VISUAL_TOOLCHAIN_MISSING: str = "toolchain_missing"

# Stage-0-OQ4: 10 % Pixel-Diff sind robust gegen Font-/OS-Nondeterminismus,
# ohne offensichtliche visuelle Regressionen zu verpassen.
DEFAULT_VISUAL_TOLERANCE: float = 0.1


@dataclass(frozen=True)
class VisualDiffResult:
    """Strukturiertes Ergebnis eines Visual-Regression-Vergleichs.

    `passed` ist `True`, wenn `diff_ratio <= tolerance`. Bei
    `reason == VISUAL_TOOLCHAIN_MISSING` ist `passed=False`, aber Tests
    sollten den Result wie ein Skip behandeln (analog Phase 5a).
    """

    passed: bool
    pixel_diff_count: int
    total_pixels: int
    diff_ratio: float
    tolerance: float
    diff_image_path: Path | None = None
    reason: str | None = None

    @property
    def toolchain_missing(self) -> bool:
        return self.reason == VISUAL_TOOLCHAIN_MISSING


class VisualDiffDriver(Protocol):
    """Pro Target ein Driver, der gerenderten Code in ein PNG rendert + Pixel-Diff macht."""

    target: str

    def is_available(self) -> bool:
        """True, wenn die Toolchain (z. B. `node` + Playwright-Browser) verfügbar ist."""
        ...

    def render(self, *, files: dict[str, bytes], work_dir: Path) -> Path:
        """Rendert `files` in `work_dir` und liefert den Pfad zum Screenshot-PNG."""
        ...

    def diff(self, *, expected: Path, actual: Path, work_dir: Path) -> tuple[int, int, Path | None]:
        """Pixel-Diff zwischen `expected` und `actual`.

        Rückgabe: `(diff_pixels, total_pixels, diff_image_path_or_None)`.
        """
        ...


# --- Playwright + pixelmatch Driver ------------------------------------------

# Stage-0-OQ1: Playwright + pixelmatch. Versions-Pins analog Phase 5a für
# Determinismus.
PLAYWRIGHT_VERSION: str = "1.44.0"
PIXELMATCH_VERSION: str = "5.3.0"
PNGJS_VERSION: str = "7.0.0"  # Dependency von pixelmatch für PNG-Decoding.


@dataclass(frozen=True)
class PlaywrightPixelmatchDriver:
    """Visual-Diff-Driver für React + Angular via headless Chromium + pixelmatch.

    Strategie:

    1. `render()` schreibt die generierten Files in eine Mini-HTML-Sandbox
       (`index.html` lädt den Code via ESM + Babel-Standalone), startet
       Playwright headless und macht einen Screenshot nach `actual.png`.
    2. `diff()` ruft `pixelmatch <expected> <actual> <diff> ...` über die
       `pixelmatch`-CLI auf (via lokales `node_modules/.bin/pixelmatch`),
       parsiert die Stdout (Format: `<diffPixels> different pixels`).

    Der eigentliche Render-Pfad ist *bewusst minimal*: keine Webpack-/Vite-
    Pipeline, kein realer Component-Mount in einem Test-Renderer — der Code
    wird in einer einfachen HTML-Page exponiert und gescreenshottet. Für ein
    Skeleton ist das ausreichend; ein vollständiger Renderer ist Folge-Phase.
    """

    target: str = "react"
    playwright_version: str = PLAYWRIGHT_VERSION
    pixelmatch_version: str = PIXELMATCH_VERSION
    pngjs_version: str = PNGJS_VERSION
    viewport_width: int = 320
    viewport_height: int = 240

    def is_available(self) -> bool:
        return shutil.which("npm") is not None and shutil.which("node") is not None

    def _package_json(self) -> dict[str, object]:
        return {
            "name": f"speccify-visual-{self.target}",
            "version": "0.0.0",
            "private": True,
            "type": "module",
            "devDependencies": {
                "playwright": self.playwright_version,
                "pixelmatch": self.pixelmatch_version,
                "pngjs": self.pngjs_version,
            },
        }

    def _index_html(self, files: dict[str, bytes]) -> str:
        # Bewusst sehr einfache Sandbox: lädt alle generierten Files als
        # plain `<pre>`-Blöcke, damit der Screenshot deterministisch wird,
        # *ohne* dass wir eine echte JS-Runtime/Framework-Bootstrap-Pipeline
        # brauchen. Phase-5c-Skeleton-Scope: Diff-Pfad funktioniert. Ein
        # echter Component-Mount ist Folge-Phase.
        snippets: list[str] = []
        for rel_path in sorted(files):
            try:
                text = files[rel_path].decode("utf-8")
            except UnicodeDecodeError:
                text = f"<binary {rel_path}>"
            escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            snippets.append(
                f'<section data-file="{rel_path}"><h2>{rel_path}</h2><pre>{escaped}</pre></section>'
            )
        body = "\n".join(snippets) if snippets else "<p>(no files)</p>"
        return (
            "<!doctype html>\n"
            "<html><head><meta charset='utf-8'>"
            "<style>"
            "body{font-family:monospace;margin:0;padding:8px;background:#fff;color:#000;}"
            "h2{font-size:12px;margin:4px 0;}"
            "pre{font-size:10px;line-height:1.2;margin:0 0 8px 0;white-space:pre-wrap;}"
            "</style></head><body>"
            f"{body}"
            "</body></html>\n"
        )

    def _screenshot_script(self, *, html_path: Path, out_path: Path) -> str:
        # Minimal Playwright-Skript als ESM. `chromium.launch()` setzt voraus,
        # dass `npx playwright install chromium` einmal lokal gelaufen ist
        # (in CI per Workflow-Step). `goto('file://...')` braucht kein Netz.
        return (
            "import { chromium } from 'playwright';\n"
            "const browser = await chromium.launch();\n"
            "const context = await browser.newContext({ viewport: "
            f"{{ width: {self.viewport_width}, height: {self.viewport_height} }}"
            " });\n"
            "const page = await context.newPage();\n"
            f"await page.goto('file://{html_path.as_posix()}');\n"
            f"await page.screenshot({{ path: '{out_path.as_posix()}', fullPage: false }});\n"
            "await browser.close();\n"
        )

    def _diff_script(self, *, expected: Path, actual: Path, diff_out: Path) -> str:
        # Pixelmatch + pngjs via Node-ESM. Liefert auf Stdout JSON
        # `{ "diff": <int>, "total": <int> }`, damit Python das robust parsen
        # kann (string-grep auf "different pixels" wäre brüchig).
        return (
            "import { readFileSync, writeFileSync } from 'node:fs';\n"
            "import { PNG } from 'pngjs';\n"
            "import pixelmatch from 'pixelmatch';\n"
            f"const img1 = PNG.sync.read(readFileSync('{expected.as_posix()}'));\n"
            f"const img2 = PNG.sync.read(readFileSync('{actual.as_posix()}'));\n"
            "const { width, height } = img1;\n"
            "const diff = new PNG({ width, height });\n"
            "const n = pixelmatch(img1.data, img2.data, diff.data, "
            "width, height, { threshold: 0.1 });\n"
            f"writeFileSync('{diff_out.as_posix()}', PNG.sync.write(diff));\n"
            "console.log(JSON.stringify({ diff: n, total: width * height }));\n"
        )

    def _ensure_node_modules(self, work_dir: Path) -> tuple[int, str]:
        (work_dir / "package.json").write_text(
            json.dumps(self._package_json(), indent=2) + "\n", encoding="utf-8"
        )
        try:
            proc = subprocess.run(
                [
                    "npm",
                    "install",
                    "--no-audit",
                    "--no-fund",
                    "--silent",
                    "--prefer-offline",
                    "--no-package-lock",
                ],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError as exc:
            return 127, f"npm nicht ausführbar: {exc}"
        except subprocess.TimeoutExpired as exc:
            return 124, f"npm install timeout nach {exc.timeout}s"
        if proc.returncode != 0:
            return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
        return 0, ""

    def render(self, *, files: dict[str, bytes], work_dir: Path) -> Path:
        rc, output = self._ensure_node_modules(work_dir)
        if rc != 0:
            raise RuntimeError(f"npm install fehlgeschlagen (rc={rc}): {output}")

        html_path = work_dir / "index.html"
        html_path.write_text(self._index_html(files), encoding="utf-8")
        actual_path = work_dir / "actual.png"
        script_path = work_dir / "screenshot.mjs"
        script_path.write_text(
            self._screenshot_script(html_path=html_path, out_path=actual_path),
            encoding="utf-8",
        )

        # Playwright-Browser sind nicht via `npm install` da; sie brauchen
        # `npx playwright install chromium` (einmalig). CI macht das in einem
        # eigenen Step; lokal ebenso. `PLAYWRIGHT_BROWSERS_PATH=0` würde sie
        # in `node_modules` ablegen — wir respektieren die Default-Location.
        env = os.environ.copy()
        try:
            proc = subprocess.run(
                ["node", str(script_path)],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=180,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"playwright-screenshot timeout nach {exc.timeout}s") from exc
        if proc.returncode != 0 or not actual_path.exists():
            raise RuntimeError(
                "playwright-screenshot fehlgeschlagen:\n"
                + (proc.stdout or "")
                + (proc.stderr or "")
            )
        return actual_path

    def diff(self, *, expected: Path, actual: Path, work_dir: Path) -> tuple[int, int, Path | None]:
        # `_ensure_node_modules` ist idempotent — wenn `render()` schon lief,
        # ist `node_modules/pixelmatch` da; sonst (z. B. nur Diff-Pfad
        # genutzt) wird es jetzt nachinstalliert.
        if not (work_dir / "node_modules" / "pixelmatch").exists():
            rc, output = self._ensure_node_modules(work_dir)
            if rc != 0:
                raise RuntimeError(f"npm install fehlgeschlagen (rc={rc}): {output}")

        diff_out = work_dir / "diff.png"
        script_path = work_dir / "diff.mjs"
        script_path.write_text(
            self._diff_script(expected=expected, actual=actual, diff_out=diff_out),
            encoding="utf-8",
        )
        try:
            proc = subprocess.run(
                ["node", str(script_path)],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"pixelmatch-diff timeout nach {exc.timeout}s") from exc
        if proc.returncode != 0:
            raise RuntimeError(
                "pixelmatch-diff fehlgeschlagen:\n" + (proc.stdout or "") + (proc.stderr or "")
            )
        try:
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
            return int(payload["diff"]), int(payload["total"]), diff_out
        except (json.JSONDecodeError, KeyError, IndexError, ValueError) as exc:
            raise RuntimeError(f"pixelmatch-Stdout nicht parsebar: {proc.stdout!r}") from exc


# --- Backend ------------------------------------------------------------------


def visual_driver_for(target: str) -> VisualDiffDriver | None:
    """Faktor-Helfer analog `build_smoke_driver_for` (Phase 5a).

    Phase-5c-Skeleton: nur Browser-Targets (React + Angular) haben einen
    Driver. SwiftUI braucht einen Xcode-UI-Test-Harness (Folge-Phase).
    """
    if target == "react":
        return PlaywrightPixelmatchDriver(target="react")
    if target == "angular":
        return PlaywrightPixelmatchDriver(target="angular")
    return None


@dataclass
class VisualRegressionBackend:
    """Vergleicht gerenderte Files mit einer committed Referenz-PNG.

    Im Gegensatz zum Build-Smoke-Backend (Phase 5a) ist die API *nicht*
    `(lockfile, registry, llm_client) -> ConformanceReport`, sondern die
    direkte Frage: „Passt der gerenderte Output zur Referenz?" — `compare()`
    nimmt explizit Files + Referenz-PNG entgegen. Eine Integration in den
    vollen `ConformanceBackend`-Pfad ist Folge-Substage (sobald `screenshots`
    aus dem Spec aufgelöst werden).
    """

    driver: VisualDiffDriver
    tolerance: float = DEFAULT_VISUAL_TOLERANCE

    def compare(
        self,
        *,
        files: dict[str, bytes],
        reference: Path,
        work_dir: Path,
    ) -> VisualDiffResult:
        if not self.driver.is_available():
            return VisualDiffResult(
                passed=False,
                pixel_diff_count=0,
                total_pixels=0,
                diff_ratio=0.0,
                tolerance=self.tolerance,
                reason=VISUAL_TOOLCHAIN_MISSING,
            )
        if not reference.exists():
            return VisualDiffResult(
                passed=False,
                pixel_diff_count=0,
                total_pixels=0,
                diff_ratio=0.0,
                tolerance=self.tolerance,
                reason=f"reference_missing: {reference}",
            )

        actual = self.driver.render(files=files, work_dir=work_dir)
        diff_pixels, total_pixels, diff_image = self.driver.diff(
            expected=reference, actual=actual, work_dir=work_dir
        )
        ratio = (diff_pixels / total_pixels) if total_pixels > 0 else 0.0
        return VisualDiffResult(
            passed=ratio <= self.tolerance,
            pixel_diff_count=diff_pixels,
            total_pixels=total_pixels,
            diff_ratio=ratio,
            tolerance=self.tolerance,
            diff_image_path=diff_image,
            reason=None if ratio <= self.tolerance else "tolerance_exceeded",
        )
