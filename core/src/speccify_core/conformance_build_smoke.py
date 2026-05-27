"""Build-Smoke-Backend für `ConformanceBackend` (Phase 5a).

Implementiert das `ConformanceBackend`-Protocol aus `conformance.py` mit echten
Toolchain-Subprozessen pro Target:

- **react** → `tsc --noEmit` über ein Mini-Projekt (`package.json`,
  `tsconfig.json`, gerenderte `.tsx`-Dateien) auf einem temporären Verzeichnis.
- **angular** → `tsc --noEmit` mit Angular-Typings (`@angular/core`,
  `@angular/common`); echtes `ng build` ist Phase-5b-Stretch.
- **swiftui** → `swiftc -typecheck` über die gerenderten `.swift`-Dateien.

Fehlt eine Toolchain auf dem aktuellen System (z. B. `swiftc` auf Linux),
liefert der Backend pro betroffenem Eintrag einen `ConformanceResult` mit
`status="toolchain_missing"` zurück. Das ist *kein* Test-Failure — Tests
können diesen Status via `result.toolchain_missing` als „skip" interpretieren.

Phase 5a fokussiert sich auf den Build-Smoke selbst; die CLI- und MCP-Pfade
binden den Backend noch nicht ein (Folge-Substage).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from speccify_core.codegen import (
    CacheMissError,
    CodegenError,
    LlmClient,
    TargetRender,
    render_for_target,
)
from speccify_core.conformance import ConformanceReport, ConformanceResult
from speccify_core.lockfile import LockEntry, Lockfile
from speccify_core.registry import Registry, RegistryError, Version

__all__ = [
    "BUILD_SMOKE_TOOLCHAIN_MISSING",
    "BuildSmokeBackend",
    "ToolchainDriver",
    "ReactToolchainDriver",
    "AngularToolchainDriver",
    "SwiftUIToolchainDriver",
    "build_smoke_driver_for",
]

# Eigener Status-Code für „Toolchain fehlt auf dieser Plattform".
# Bewusst kein Failure: Tests sollen diesen Status zu `pytest.skip` mappen.
BUILD_SMOKE_TOOLCHAIN_MISSING: str = "toolchain_missing"


class ToolchainDriver(Protocol):
    """Pro Target ein Driver, der gerenderte Files auf Disk schreibt + Build aufruft."""

    target: str

    def is_available(self) -> bool:
        """True, wenn die Toolchain (z. B. `node`/`npx`/`swiftc`) auf dem System verfügbar ist."""
        ...

    def build(self, *, files: dict[str, bytes], work_dir: Path) -> tuple[int, str]:
        """Schreibt `files` in `work_dir` und führt den Build-Smoke aus.

        Rückgabe: `(returncode, combined_stdout_stderr)`. `returncode == 0` heißt
        Build-Smoke OK.
        """
        ...


# --- React-Driver -------------------------------------------------------------

# TypeScript-Version explizit gepinnt (Stage-0-Decision OQ1: deterministische
# Versionen). `npx --package=typescript@<pin>` zieht das Paket on-demand;
# kein globales Install nötig.
REACT_TYPESCRIPT_VERSION: str = "5.4.5"
REACT_TYPES_VERSION: str = "18.2.79"

_REACT_TSCONFIG: dict[str, object] = {
    "compilerOptions": {
        "target": "ES2020",
        "module": "ESNext",
        "moduleResolution": "Bundler",
        "jsx": "react-jsx",
        "strict": True,
        "esModuleInterop": True,
        "skipLibCheck": True,
        "noEmit": True,
        "isolatedModules": True,
        "allowSyntheticDefaultImports": True,
    },
    "include": ["**/*.ts", "**/*.tsx"],
}

_REACT_PACKAGE_JSON: dict[str, object] = {
    "name": "speccify-conformance-react",
    "version": "0.0.0",
    "private": True,
    "type": "module",
    "devDependencies": {
        "typescript": REACT_TYPESCRIPT_VERSION,
        "@types/react": REACT_TYPES_VERSION,
    },
}


@dataclass(frozen=True)
class ReactToolchainDriver:
    """Build-Smoke-Driver für React-Outputs via `tsc --noEmit`.

    Strategie: legt im Work-Dir eine minimale TypeScript-Projektshell an
    (`package.json` mit `typescript` + `@types/react` als devDeps,
    `tsconfig.json` mit `jsx=react-jsx`, `strict=true`, `noEmit=true`),
    schreibt die gerenderten Files dahinein und ruft `npx --package=...`
    auf, sodass eine deterministische `typescript`-Version verwendet wird.
    Kein globales `tsc`-Install nötig — nur `node`/`npx`.
    """

    target: str = "react"
    typescript_version: str = REACT_TYPESCRIPT_VERSION
    types_react_version: str = REACT_TYPES_VERSION

    def is_available(self) -> bool:
        return shutil.which("npm") is not None and shutil.which("node") is not None

    def build(self, *, files: dict[str, bytes], work_dir: Path) -> tuple[int, str]:
        # Files schreiben (Pfade können Sub-Verzeichnisse enthalten).
        for rel_path, blob in files.items():
            target_path = work_dir / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(blob)

        (work_dir / "package.json").write_text(
            json.dumps(_REACT_PACKAGE_JSON, indent=2) + "\n", encoding="utf-8"
        )
        (work_dir / "tsconfig.json").write_text(
            json.dumps(_REACT_TSCONFIG, indent=2) + "\n", encoding="utf-8"
        )

        # Schritt 1: `npm install` legt `<work_dir>/node_modules/typescript` +
        # `<work_dir>/node_modules/@types/react` an. Wir nutzen `npm` statt
        # `npx --package=...`, weil letzteres die Packages in einen globalen
        # npx-Cache zieht — `tsc` findet die @types-Pakete dann nicht über
        # die normale Modulauflösung (Stage-1-Lehre: TS7026 ohne lokales
        # `node_modules`). Mit `--no-audit --no-fund --silent --prefer-offline`
        # bleibt der Output knapp und reproduzierbar.
        install_cmd = [
            "npm",
            "install",
            "--no-audit",
            "--no-fund",
            "--silent",
            "--prefer-offline",
            "--no-package-lock",
        ]
        try:
            install_proc = subprocess.run(
                install_cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=240,
            )
        except FileNotFoundError as exc:
            return 127, f"npm nicht ausführbar: {exc}"
        except subprocess.TimeoutExpired as exc:
            return 124, f"npm install timeout nach {exc.timeout}s"

        if install_proc.returncode != 0:
            return install_proc.returncode, (
                "npm install fehlgeschlagen:\n"
                + (install_proc.stdout or "")
                + (install_proc.stderr or "")
            )

        # Schritt 2: `tsc --noEmit` über den lokalen `node_modules/.bin/tsc`.
        tsc_bin = work_dir / "node_modules" / ".bin" / "tsc"
        if not tsc_bin.exists():
            return 127, f"tsc-Binary nicht gefunden unter {tsc_bin}"

        tsc_cmd = [
            str(tsc_bin),
            "--noEmit",
            "--project",
            str(work_dir / "tsconfig.json"),
        ]
        try:
            tsc_proc = subprocess.run(
                tsc_cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired as exc:
            return 124, f"tsc-Build-Smoke timeout nach {exc.timeout}s"

        combined = (tsc_proc.stdout or "") + (tsc_proc.stderr or "")
        return tsc_proc.returncode, combined


# --- Angular-Driver -----------------------------------------------------------

# Stage-0-OQ1: deterministische Toolchain-Pins. `@angular/core` + `@angular/common`
# liefern die Typings für `@Component`, `signal`, etc.; `tsc --noEmit` mit
# `experimentalDecorators`/`emitDecoratorMetadata` reicht als Smoke. Vollständiges
# `ng build` ist Phase-5b-Stretch (Plan-Stage-2).
ANGULAR_TYPESCRIPT_VERSION: str = "5.4.5"
ANGULAR_CORE_VERSION: str = "17.3.0"
ANGULAR_COMMON_VERSION: str = "17.3.0"
ANGULAR_RXJS_VERSION: str = "7.8.1"
ANGULAR_ZONE_VERSION: str = "0.14.4"

_ANGULAR_TSCONFIG: dict[str, object] = {
    "compilerOptions": {
        "target": "ES2022",
        "module": "ES2022",
        "moduleResolution": "Bundler",
        "experimentalDecorators": True,
        "emitDecoratorMetadata": True,
        "useDefineForClassFields": False,
        "strict": True,
        "esModuleInterop": True,
        "skipLibCheck": True,
        "noEmit": True,
        "isolatedModules": True,
        "lib": ["ES2022", "DOM"],
    },
    "include": ["**/*.ts"],
}

_ANGULAR_PACKAGE_JSON: dict[str, object] = {
    "name": "speccify-conformance-angular",
    "version": "0.0.0",
    "private": True,
    "type": "module",
    "devDependencies": {
        "typescript": ANGULAR_TYPESCRIPT_VERSION,
        "@angular/core": ANGULAR_CORE_VERSION,
        "@angular/common": ANGULAR_COMMON_VERSION,
        "rxjs": ANGULAR_RXJS_VERSION,
        "zone.js": ANGULAR_ZONE_VERSION,
    },
}


@dataclass(frozen=True)
class AngularToolchainDriver:
    """Build-Smoke-Driver für Angular-Outputs via `tsc --noEmit` + Angular-Typings.

    Strategie analog `ReactToolchainDriver`: minimale TypeScript-Projektshell mit
    `@angular/core`/`@angular/common` als devDeps, `experimentalDecorators=true`,
    `emitDecoratorMetadata=true`. `npm install` lädt die Pakete nach
    `<work_dir>/node_modules`, anschließend läuft der lokale
    `node_modules/.bin/tsc --noEmit`. Echtes `ng build` ist Phase-5b-Stretch.
    """

    target: str = "angular"
    typescript_version: str = ANGULAR_TYPESCRIPT_VERSION
    angular_core_version: str = ANGULAR_CORE_VERSION
    angular_common_version: str = ANGULAR_COMMON_VERSION
    rxjs_version: str = ANGULAR_RXJS_VERSION
    zone_version: str = ANGULAR_ZONE_VERSION

    def is_available(self) -> bool:
        return shutil.which("npm") is not None and shutil.which("node") is not None

    def build(self, *, files: dict[str, bytes], work_dir: Path) -> tuple[int, str]:
        for rel_path, blob in files.items():
            target_path = work_dir / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(blob)

        (work_dir / "package.json").write_text(
            json.dumps(_ANGULAR_PACKAGE_JSON, indent=2) + "\n", encoding="utf-8"
        )
        (work_dir / "tsconfig.json").write_text(
            json.dumps(_ANGULAR_TSCONFIG, indent=2) + "\n", encoding="utf-8"
        )

        # Wie beim React-Driver: `npm install` legt die devDeps lokal nach
        # `<work_dir>/node_modules/` ab, damit `tsc` die `@angular/core`-Typings
        # über die normale Modulauflösung findet. `npx --package=...` würde die
        # Pakete im npx-Cache landen lassen und `tsc` fände sie nicht.
        install_cmd = [
            "npm",
            "install",
            "--no-audit",
            "--no-fund",
            "--silent",
            "--prefer-offline",
            "--no-package-lock",
        ]
        try:
            install_proc = subprocess.run(
                install_cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError as exc:
            return 127, f"npm nicht ausführbar: {exc}"
        except subprocess.TimeoutExpired as exc:
            return 124, f"npm install timeout nach {exc.timeout}s"

        if install_proc.returncode != 0:
            return install_proc.returncode, (
                "npm install fehlgeschlagen:\n"
                + (install_proc.stdout or "")
                + (install_proc.stderr or "")
            )

        tsc_bin = work_dir / "node_modules" / ".bin" / "tsc"
        if not tsc_bin.exists():
            return 127, f"tsc-Binary nicht gefunden unter {tsc_bin}"

        tsc_cmd = [
            str(tsc_bin),
            "--noEmit",
            "--project",
            str(work_dir / "tsconfig.json"),
        ]
        try:
            tsc_proc = subprocess.run(
                tsc_cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=240,
            )
        except subprocess.TimeoutExpired as exc:
            return 124, f"tsc/Angular-Build-Smoke timeout nach {exc.timeout}s"

        combined = (tsc_proc.stdout or "") + (tsc_proc.stderr or "")
        return tsc_proc.returncode, combined


# --- SwiftUI-Driver -----------------------------------------------------------


@dataclass(frozen=True)
class SwiftUIToolchainDriver:
    """Build-Smoke-Driver für SwiftUI-Outputs via `swiftc -typecheck`.

    Strategie: gerenderte `.swift`-Files werden in `work_dir` geschrieben und
    `swiftc -typecheck` aufgerufen (kein Linking, keine Binary). Auf macOS wird
    automatisch das aktuelle SDK + die SwiftUI/Foundation-Frameworks gefunden;
    Linux-CI hat kein `swiftc` für SwiftUI-Frameworks, daher liefert
    `is_available()` dort `False` und der Backend reportet `toolchain_missing`.

    Im Gegensatz zu React/Angular gibt es kein Package-Manifest — `swiftc`
    arbeitet auf File-Ebene.
    """

    target: str = "swiftui"

    def is_available(self) -> bool:
        # `swiftc` allein reicht nicht: SwiftUI-Framework braucht macOS-SDK.
        # `xcrun` ist der zuverlässige Indikator für eine funktionsfähige
        # Xcode-/CommandLineTools-Installation auf macOS.
        return shutil.which("swiftc") is not None and shutil.which("xcrun") is not None

    def build(self, *, files: dict[str, bytes], work_dir: Path) -> tuple[int, str]:
        swift_files: list[str] = []
        for rel_path, blob in files.items():
            target_path = work_dir / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(blob)
            if rel_path.endswith(".swift"):
                swift_files.append(str(target_path))

        if not swift_files:
            return 2, "Keine .swift-Dateien zum Typchecken gefunden."

        # `xcrun --sdk macosx swiftc -typecheck` löst SDK + SwiftUI-Framework
        # automatisch auf. `-target` wird bewusst nicht gesetzt — der Default
        # passt zur Host-Architektur (arm64/x86_64).
        cmd = [
            "xcrun",
            "--sdk",
            "macosx",
            "swiftc",
            "-typecheck",
            *swift_files,
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=180,
            )
        except FileNotFoundError as exc:
            return 127, f"xcrun/swiftc nicht ausführbar: {exc}"
        except subprocess.TimeoutExpired as exc:
            return 124, f"swiftc-Build-Smoke timeout nach {exc.timeout}s"

        combined = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, combined


# --- Backend ------------------------------------------------------------------


def build_smoke_driver_for(target: str) -> ToolchainDriver | None:
    """Faktor-Helfer: liefert den passenden Driver oder `None`, wenn unbekannt."""
    if target == "react":
        return ReactToolchainDriver()
    if target == "angular":
        return AngularToolchainDriver()
    if target == "swiftui":
        return SwiftUIToolchainDriver()
    return None


@dataclass
class BuildSmokeBackend:
    """`ConformanceBackend`-Implementierung mit echten Toolchain-Aufrufen.

    Pro Lockfile-Eintrag:
      1. Spec aus Registry laden.
      2. Re-Rendern (gleicher Pfad wie `StaticValidateBackend`).
      3. Ist der Target-Driver verfügbar → Files in `tmp_dir/<target>/<spec>`
         schreiben, Driver aufrufen. `returncode == 0` → `status="ok"`,
         sonst `status="build_failed"` mit Stdout/Stderr in `messages`.
      4. Fehlt der Driver oder die Toolchain → `status="toolchain_missing"`
         (kein Failure, kein OK — Tests skippen).

    `drivers` kann von Tests überschrieben werden, um einen Fake einzuschleusen.
    """

    name: str = field(default="build-smoke")
    drivers: dict[str, ToolchainDriver] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.drivers:
            # Default-Driver-Registry: alle drei Phase-5a-Targets aktiv.
            # Jeder Driver entscheidet selbst via `is_available()`, ob die
            # Toolchain auf dem aktuellen System nutzbar ist (z. B. `swiftc`
            # nur auf macOS).
            self.drivers = {
                "react": ReactToolchainDriver(),
                "angular": AngularToolchainDriver(),
                "swiftui": SwiftUIToolchainDriver(),
            }

    def run(
        self,
        *,
        lockfile: Lockfile,
        registry: Registry,
        llm_client: LlmClient,
        targets: tuple[str, ...] | None = None,
    ) -> ConformanceReport:
        wanted: set[str] | None = set(targets) if targets else None
        results: list[ConformanceResult] = []
        for entry in lockfile.entries:
            if wanted is not None and entry.target not in wanted:
                continue
            results.append(
                self._run_one(entry, registry=registry, llm_client=llm_client),
            )
        return ConformanceReport(results=tuple(results), backend=self.name)

    def _run_one(
        self,
        entry: LockEntry,
        *,
        registry: Registry,
        llm_client: LlmClient,
    ) -> ConformanceResult:
        driver = self.drivers.get(entry.target)
        if driver is None:
            return ConformanceResult(
                spec_id=entry.id,
                version=entry.version,
                target=entry.target,
                status=BUILD_SMOKE_TOOLCHAIN_MISSING,
                messages=(f"Kein Build-Smoke-Driver für Target '{entry.target}' registriert.",),
            )
        if not driver.is_available():
            return ConformanceResult(
                spec_id=entry.id,
                version=entry.version,
                target=entry.target,
                status=BUILD_SMOKE_TOOLCHAIN_MISSING,
                messages=(
                    f"Toolchain für Target '{entry.target}' auf diesem System nicht verfügbar.",
                ),
            )

        # 1) Spec laden
        try:
            spec = registry.fetch(entry.id, Version.parse(entry.version))
        except RegistryError as exc:
            return ConformanceResult(
                spec_id=entry.id,
                version=entry.version,
                target=entry.target,
                status="render_failed",
                messages=(f"Spec konnte nicht geladen werden: {exc}",),
            )

        # 2) Re-Render
        try:
            rendered: TargetRender = render_for_target(spec, entry.target, llm_client=llm_client)
        except (CacheMissError, CodegenError, NotImplementedError) as exc:
            return ConformanceResult(
                spec_id=entry.id,
                version=entry.version,
                target=entry.target,
                status="render_failed",
                messages=(f"Re-Render fehlgeschlagen: {exc}",),
            )

        # 3) Build-Smoke in tmp-Dir
        with tempfile.TemporaryDirectory(prefix="speccify-buildsmoke-") as raw_tmp:
            work_dir = Path(raw_tmp)
            returncode, output = driver.build(files=dict(rendered.files), work_dir=work_dir)

        if returncode == 0:
            return ConformanceResult(
                spec_id=entry.id,
                version=entry.version,
                target=entry.target,
                status="ok",
            )

        # Build fehlgeschlagen → Output knapp halten, damit Pytest-Diff lesbar bleibt.
        snippet = output.strip()
        if len(snippet) > 2000:
            snippet = snippet[:2000] + "\n…(truncated)"
        return ConformanceResult(
            spec_id=entry.id,
            version=entry.version,
            target=entry.target,
            status="build_failed",
            messages=(
                f"Build-Smoke fehlgeschlagen (returncode={returncode}).",
                snippet,
            ),
        )
