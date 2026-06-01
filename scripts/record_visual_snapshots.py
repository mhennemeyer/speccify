"""Maintainer-Tool: nimmt Referenz-Screenshots für den Visual-Regression-Sweep auf.

Phase 5d Stage 1: Single-Source-of-Truth-Recorder — ruft den
`PlaywrightPixelmatchDriver` *direkt* im Render-Modus auf (OQ3 = a), schreibt
die resultierende PNG nach `specs/screenshots/<spec-name>-<target>.png` (flache
Namens-Konvention, OQ1 = a).

Idempotenz: Zwei aufeinanderfolgende Läufe sollen byte-identische PNGs
produzieren (Determinismus-Härte mittel, OQ4 = b — Viewport + reduce-motion +
color-scheme:light + monospace-Font-Stack stecken im Driver/HTML-Sandbox).

`http-api-client` ist headless und nicht im Sweep (ZQ1).

Beispiele:

    # Alle 8 PNGs (4 UI-Specs × {react, angular}) regenerieren:
    python scripts/record_visual_snapshots.py --all

    # Nur eine Kombination:
    python scripts/record_visual_snapshots.py --spec button --target react

Voraussetzung:
- Node + npm + Playwright-Chromium-Install (`npx playwright install chromium`).
- Eingecheckte Replay-Cache-Fixtures unter `tests/fixtures/llm-cache/`
  (kein Netz nötig).
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = REPO_ROOT / "registry-fixtures"
DEFAULT_CACHE_DIR = REPO_ROOT / "tests" / "fixtures" / "llm-cache"
DEFAULT_OUT = REPO_ROOT / "specs" / "screenshots"

# UI-Specs aus Phase-0-Audit. `http-api-client` ist headless → ausgeschlossen.
UI_SPECS: tuple[str, ...] = ("button", "contact-form", "login-screen", "onboarding-wizard")
TARGETS: tuple[str, ...] = ("react", "angular")
SCOPE: str = "org"


def _ensure_venv_pth_visible() -> None:
    """macOS-Workaround analog `record_llm_cache.py` (siehe AGENTS.md, Hinweis 6)."""
    if sys.platform != "darwin":
        return
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from _venv_hygiene import unhide_venv_deep, unhide_venv_pth_files
    except ImportError:
        return

    candidates: list[Path] = []
    active = Path(sys.prefix)
    if active.is_dir() and (active / "lib").is_dir():
        candidates.append(active)
    repo_venv = REPO_ROOT / ".venv"
    if repo_venv.is_dir() and repo_venv.resolve() != active.resolve():
        candidates.append(repo_venv)

    for venv in candidates:
        unhide_venv_pth_files(venv)

    import importlib
    import importlib.util
    import site

    importlib.reload(site)
    site.main()

    if importlib.util.find_spec("speccify_core") is None:
        for venv in candidates:
            unhide_venv_deep(venv)
        importlib.reload(site)
        site.main()


_ensure_venv_pth_visible()


def _latest_version(registry, spec_id: str):  # type: ignore[no-untyped-def]
    """Liefert die neueste verfügbare Version einer Spec aus dem Registry."""
    versions = sorted(registry.list_versions(spec_id))
    if not versions:
        raise RuntimeError(f"Keine Versionen für {spec_id} im Registry gefunden.")
    return versions[-1]


def _render_snapshot(
    *,
    spec_name: str,
    target: str,
    fixtures_root: Path,
    cache_dir: Path,
    out_dir: Path,
) -> Path:
    """Rendert eine Spec für `target` und schreibt die PNG nach `out_dir`."""
    from speccify_core import (
        LocalRegistry,
        PlaywrightPixelmatchDriver,
        ReplayCache,
        ReplayCacheClient,
        render_for_target,
    )

    registry = LocalRegistry(fixtures_root)
    spec_id = f"@{SCOPE}/{spec_name}"
    version = _latest_version(registry, spec_id)
    spec = registry.fetch(spec_id, version)

    cache = ReplayCache(cache_dir)
    llm_client = ReplayCacheClient(cache=cache)
    rendered = render_for_target(spec, target, llm_client=llm_client)

    driver = PlaywrightPixelmatchDriver(target=target)
    if not driver.is_available():
        raise RuntimeError(
            "node/npm nicht verfügbar — Recorder benötigt die Visual-Regression-Toolchain."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{spec_name}-{target}.png"

    with tempfile.TemporaryDirectory(prefix=f"speccify-visual-{spec_name}-{target}-") as tmp:
        work_dir = Path(tmp)
        actual = driver.render(files=rendered.files, work_dir=work_dir)
        # Atomar überschreiben — vermeidet halb-geschriebene PNGs bei Abbruch.
        shutil.copyfile(actual, out_path)

    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=str, default=None, help=f"Spec-Name (eines aus {UI_SPECS}).")
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        choices=list(TARGETS),
        help="Codegen-Target (react|angular).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=f"Alle {len(UI_SPECS) * len(TARGETS)} Kombinationen regenerieren.",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="Registry-Wurzel (Default: ./registry-fixtures).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Replay-Cache-Verzeichnis (Default: ./tests/fixtures/llm-cache).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output-Verzeichnis (Default: ./specs/screenshots).",
    )
    args = parser.parse_args(argv)

    if args.all:
        combos = [(s, t) for s in UI_SPECS for t in TARGETS]
    else:
        if args.spec is None or args.target is None:
            parser.error("Entweder --all oder beide --spec und --target angeben.")
        if args.spec not in UI_SPECS:
            parser.error(f"--spec muss eines aus {UI_SPECS} sein (got: {args.spec!r}).")
        combos = [(args.spec, args.target)]

    failed: list[tuple[str, str, str]] = []
    written: list[Path] = []
    for spec_name, target in combos:
        label = f"{spec_name}/{target}"
        print(f"[render] {label} …", flush=True)
        try:
            out_path = _render_snapshot(
                spec_name=spec_name,
                target=target,
                fixtures_root=args.fixtures,
                cache_dir=args.cache_dir,
                out_dir=args.out,
            )
        except Exception as exc:  # noqa: BLE001 — Recorder zeigt Fehler an
            print(f"  ✗ {label}: {exc}", file=sys.stderr)
            failed.append((spec_name, target, str(exc)))
            continue
        size = out_path.stat().st_size
        print(f"  ✓ {label} → {out_path.relative_to(REPO_ROOT)} ({size} bytes)")
        written.append(out_path)

    print()
    print(f"Recorded: {len(written)}, failed: {len(failed)}")
    for spec_name, target, reason in failed:
        print(f"  - {spec_name}/{target}: {reason}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
