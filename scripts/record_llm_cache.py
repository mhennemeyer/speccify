"""Maintainer-Tool: nimmt Replay-Cache-Einträge für Phase-0-Specs auf.

Phase 1b Step 5: CI läuft mit `pull --offline` ausschließlich gegen den
eingecheckten Replay-Cache unter `tests/fixtures/llm-cache/`. Wenn sich eine
Spec, der Prompt oder der Modell-Pin ändert, müssen die Cache-Einträge neu
aufgenommen werden — genau dafür ist dieses Skript da.

Voraussetzung:
- AWS-Credentials in der Umgebung (`AWS_REGION`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY` — oder ein `AWS_PROFILE`); eine `.env`-Datei am
  Repo-Root wird automatisch geladen, falls vorhanden,
- `boto3` SDK installiert (`uv sync --extra bedrock`).

Verhalten:
- Lädt alle Specs aus `registry-fixtures/` (alle Versionen).
- Für jede Spec: baut Cache-Key via `react_llm.make_cache_key`, prüft ob ein
  Eintrag im Ziel-Cache existiert. Wenn ja → skip (idempotent), außer
  `--force`.
- Bei Cache-Miss: ruft Live-`BedrockClient`, normalisiert TSX, validiert
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
    from speccify_core.codegen.react_llm import (
        MODEL,
        build_prompt,
        make_cache_key,
        normalize_tsx,
        validate_tsx,
    )

    cache = ReplayCache(args.cache_dir)
    client = BedrockClient(region=region)

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
        except BedrockClientError as exc:
            print(f"    ✗ Bedrock-Fehler: {exc}", file=sys.stderr)
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
