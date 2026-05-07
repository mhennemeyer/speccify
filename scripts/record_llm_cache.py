"""Maintainer-Tool: nimmt Replay-Cache-Einträge für Phase-0-Specs auf.

Phase 1b Step 5: CI läuft mit `pull --offline` ausschließlich gegen den
eingecheckten Replay-Cache unter `tests/fixtures/llm-cache/`. Wenn sich eine
Spec, der Prompt oder der Modell-Pin ändert, müssen die Cache-Einträge neu
aufgenommen werden — genau dafür ist dieses Skript da.

Voraussetzung:
- `ANTHROPIC_API_KEY` in der Umgebung,
- `anthropic` SDK installiert (`uv sync --extra anthropic`).

Verhalten:
- Lädt alle Specs aus `registry-fixtures/` (alle Versionen).
- Für jede Spec: baut Cache-Key via `react_llm.make_cache_key`, prüft ob ein
  Eintrag im Ziel-Cache existiert. Wenn ja → skip (idempotent), außer
  `--force`.
- Bei Cache-Miss: ruft Live-`AnthropicClient`, normalisiert TSX, validiert
  Klammer-Heuristik und legt das Ergebnis im Cache ab.
- Druckt eine Zusammenfassung (recorded / cached / failed).

Bewusst kein Pytest-Eintrag: Skript greift aufs Netz zu und muss manuell
laufen.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = REPO_ROOT / "registry-fixtures"
DEFAULT_CACHE_DIR = REPO_ROOT / "tests" / "fixtures" / "llm-cache"


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
        "--force",
        action="store_true",
        help="Auch bei Cache-Hit neu aufnehmen (überschreibt Eintrag).",
    )
    args = parser.parse_args(argv)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY ist nicht gesetzt.", file=sys.stderr)
        return 1

    # Imports erst hier, damit `--help` ohne installierte Deps funktioniert.
    from speccify_core.codegen import ReplayCache
    from speccify_core.codegen.anthropic_client import AnthropicClient, AnthropicClientError
    from speccify_core.codegen.react_llm import (
        MODEL,
        build_prompt,
        make_cache_key,
        normalize_tsx,
        validate_tsx,
    )

    cache = ReplayCache(args.cache_dir)
    client = AnthropicClient(api_key=api_key)

    recorded = 0
    cached = 0
    failed: list[tuple[str, str]] = []

    for spec in _iter_specs(args.fixtures):
        label = f"{spec.spec_id}@{spec.version}"
        key = make_cache_key(spec)
        if cache.has(key) and not args.force:
            print(f"  [cached] {label} (digest={key.digest()[:12]}…)")
            cached += 1
            continue

        prompt = build_prompt(spec)
        print(f"  [record] {label} (model={MODEL})")
        try:
            raw = client.complete(prompt=prompt, model=MODEL, seed=key.seed)
        except AnthropicClientError as exc:
            print(f"    ✗ Anthropic-Fehler: {exc}", file=sys.stderr)
            failed.append((label, str(exc)))
            continue

        try:
            text = normalize_tsx(raw)
            validate_tsx(text)
        except Exception as exc:  # noqa: BLE001 — wir zeigen den Fehler an
            print(f"    ✗ TSX-Validierung fehlgeschlagen: {exc}", file=sys.stderr)
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
