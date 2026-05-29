"""Maintainer-Tool: nimmt Replay-Cache-Einträge für Phase-0-Specs auf.

Phase 1b Step 5: CI läuft mit `pull --offline` ausschließlich gegen den
eingecheckten Replay-Cache unter `tests/fixtures/llm-cache/`. Wenn sich eine
Spec, der Prompt oder der Modell-Pin ändert, müssen die Cache-Einträge neu
aufgenommen werden — genau dafür ist dieses Skript da.

Phase 5b Stage 1: das Skript ist jetzt **target-aware**. Per `--target` lässt
sich die Aufnahme für `react` (Default, unverändertes Phase-1b-Verhalten),
`angular`, `swiftui`, `all` oder eine Komma-Liste (`angular,swiftui`)
auslösen. Pro Target werden das passende `*_llm`-Modul (Prompt, MODEL,
make_cache_key, normalize/validate) verwendet — der gemeinsame
Replay-Cache-Pfad bleibt `tests/fixtures/llm-cache/` (OQ3 = A).

Voraussetzung:
- AWS-Credentials in der Umgebung (`AWS_REGION`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY` — oder ein `AWS_PROFILE`); eine `.env`-Datei am
  Repo-Root wird automatisch geladen, falls vorhanden,
- `boto3` SDK installiert (`uv sync --extra bedrock`).

Verhalten:
- Lädt alle Specs aus `registry-fixtures/` (alle Versionen) **einmal**.
- Für jedes gewählte Target und jede Spec: baut Cache-Key via
  `<target>_llm.make_cache_key`, prüft ob ein Eintrag im Ziel-Cache existiert.
  Wenn ja → skip (idempotent), außer `--force`.
- Bei Cache-Miss: ruft Live-`BedrockClient`, normalisiert + validiert das
  Ergebnis target-spezifisch und legt den **rohen** Response im Cache ab.
- Druckt eine Zusammenfassung (recorded / cached / failed).

Bewusst kein Pytest-Eintrag: Skript greift aufs Netz zu und muss manuell
laufen. Typischer Phase-5b-Workflow:

    BEDROCK_RECORD=1 .venv/bin/python scripts/record_llm_cache.py \\
        --target angular,swiftui
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = REPO_ROOT / "registry-fixtures"
DEFAULT_CACHE_DIR = REPO_ROOT / "tests" / "fixtures" / "llm-cache"


def _ensure_venv_pth_visible() -> None:
    """macOS-Workaround: `.pth`-Dateien (und ggf. versteckte Subdirs/`.py`-
    Dateien) im **aktiven** venv entversteckten, bevor wir `speccify_core`
    importieren. Pytest tut das automatisch via `conftest.py`; Standalone-
    Skripte wie dieses müssen den Hook selbst triggern, sonst bricht der
    Import mit `ModuleNotFoundError` (siehe AGENTS.md, Hinweis 6).

    Robustheit gegen `uv run`: `uv run` setzt `sys.prefix` auf das von ihm
    verwaltete venv — das ist **nicht** zwangsläufig `<repo>/.venv`. Wir
    entversteckten daher primär `sys.prefix` und zusätzlich (defensiv)
    `<repo>/.venv`. Falls nach dem flachen Sweep der Import immer noch
    fehlschlägt, ziehen wir transparent den `--deep`-Sweep nach (versteckte
    Subdirs + `.py`-Dateien). No-Op außerhalb macOS.
    """
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

    # `site.py` hat die (damals versteckten) `.pth`-Dateien beim Interpreter-
    # Start ignoriert — jetzt, wo sie sichtbar sind, müssen wir `site.main()`
    # erneut laufen lassen, damit die editable-Workspace-Pfade in `sys.path`
    # landen. Sonst nützt das Entversteckten nichts für den aktuellen Prozess.
    import importlib
    import site

    importlib.reload(site)
    site.main()

    # Sanity-Check: lässt sich `speccify_core` jetzt finden? Falls nicht,
    # ziehen wir den teuren `--deep`-Sweep nach (versteckte Subdirs +
    # `.py`-Dateien) und re-loaden `site` nochmal.
    import importlib.util

    if importlib.util.find_spec("speccify_core") is None:
        for venv in candidates:
            unhide_venv_deep(venv)
        importlib.reload(site)
        site.main()


_ensure_venv_pth_visible()


def _load_dotenv(path: Path) -> None:
    """Minimaler `.env`-Loader: setzt `KEY=VALUE` in `os.environ`, ohne `python-dotenv`.

    Bestehende Env-Vars werden nicht überschrieben (Shell-Exports gewinnen).
    Kommentare (`#`) und leere Zeilen werden ignoriert; einfache/doppelte
    Quotes um den Wert werden entfernt. Bewusst sehr defensiv — eine fehlende
    Datei ist ein No-Op.
    """
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def _iter_specs(fixtures_root: Path):  # type: ignore[no-untyped-def]
    """Walk `<root>/<scope>/<name>/<version>/spec.speccify.yaml` deterministisch."""
    from speccify_core import LocalRegistry, Version

    registry = LocalRegistry(fixtures_root)
    for scope_dir in sorted(p for p in fixtures_root.iterdir() if p.is_dir()):
        for name_dir in sorted(p for p in scope_dir.iterdir() if p.is_dir()):
            spec_id = f"@{scope_dir.name}/{name_dir.name}"
            for version_dir in sorted(p for p in name_dir.iterdir() if p.is_dir()):
                if not (version_dir / "spec.speccify.yaml").is_file():
                    continue
                try:
                    version = Version.parse(version_dir.name)
                except ValueError:
                    continue
                yield registry.fetch(spec_id, version)


_SUPPORTED_TARGETS = ("react", "angular", "swiftui")


def _resolve_targets(raw: str) -> list[str]:
    """Parst `--target`-Argument: `all` oder Komma-Liste."""
    if raw == "all":
        return list(_SUPPORTED_TARGETS)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    invalid = [p for p in parts if p not in _SUPPORTED_TARGETS]
    if invalid:
        raise SystemExit(
            f"Unbekannte Target(s): {invalid}. Erlaubt: {list(_SUPPORTED_TARGETS)} oder 'all'."
        )
    return parts


def _load_target_module(target: str):  # type: ignore[no-untyped-def]
    """Liefert (module, normalize_fn, validate_fn) für ein Target."""
    if target == "react":
        from speccify_core.codegen import react_llm as mod

        return mod, mod.normalize_tsx, mod.validate_tsx
    if target == "angular":
        from speccify_core.codegen import angular_llm as mod

        return mod, mod.normalize_ts, mod.validate_ts
    if target == "swiftui":
        from speccify_core.codegen import swiftui_llm as mod

        return mod, mod.normalize_swift, mod.validate_swift
    raise ValueError(f"Unbekanntes Target: {target}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="Registry-Wurzel mit Phase-0-Specs (Default: ./registry-fixtures).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Zielverzeichnis für Cache-Einträge (Default: ./tests/fixtures/llm-cache).",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="react",
        help=(
            "Codegen-Target(s) für die Aufnahme: 'react' (Default, Phase-1b-Verhalten), "
            "'angular', 'swiftui', 'all' oder Komma-Liste (z. B. 'angular,swiftui')."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Auch bei Cache-Hit neu aufnehmen (überschreibt Eintrag).",
    )
    args = parser.parse_args(argv)

    targets = _resolve_targets(args.target)

    _load_dotenv(REPO_ROOT / ".env")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if not (os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_PROFILE")):
        print(
            "ERROR: Keine AWS-Credentials gefunden (`AWS_ACCESS_KEY_ID` oder "
            "`AWS_PROFILE`). Bitte `.env` setzen oder Vars exportieren.",
            file=sys.stderr,
        )
        return 1

    # Imports erst hier, damit `--help` ohne installierte Deps funktioniert.
    from speccify_core.codegen import ReplayCache
    from speccify_core.codegen.bedrock_client import BedrockClient, BedrockClientError

    cache = ReplayCache(args.cache_dir)
    client = BedrockClient(region=region)

    recorded = 0
    cached = 0
    failed: list[tuple[str, str]] = []

    specs = list(_iter_specs(args.fixtures))
    for target in targets:
        mod, normalize_fn, validate_fn = _load_target_module(target)
        print(f"=== target={target} (model={mod.MODEL}) ===")
        for spec in specs:
            label = f"{target}:{spec.spec_id}@{spec.version}"
            key = mod.make_cache_key(spec)
            if cache.has(key) and not args.force:
                print(f"  [cached] {label} (digest={key.digest()[:12]}…)")
                cached += 1
                continue

            prompt = mod.build_prompt(spec)
            print(f"  [record] {label}")
            try:
                raw = client.complete(prompt=prompt, model=mod.MODEL, seed=key.seed)
            except BedrockClientError as exc:
                print(f"    ✗ Bedrock-Fehler: {exc}", file=sys.stderr)
                failed.append((label, str(exc)))
                continue

            try:
                text = normalize_fn(raw)
                validate_fn(text)
            except Exception as exc:  # noqa: BLE001 — wir zeigen den Fehler an
                print(f"    ✗ Validierung fehlgeschlagen: {exc}", file=sys.stderr)
                failed.append((label, f"validation: {exc}"))
                continue

            # Wir cachen den **rohen** Response (vor Normalisierung), damit ein
            # Re-Run mit geänderter Normalisierung den Cache nicht invalidiert,
            # solange der Modell-Output stabil bleibt.
            cache.put(key, raw)
            recorded += 1

    print()
    print(f"Recorded: {recorded}, cached (skipped): {cached}, failed: {len(failed)}")
    for label, reason in failed:
        print(f"  - {label}: {reason}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
