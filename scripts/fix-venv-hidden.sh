#!/usr/bin/env bash
# macOS-Workaround: `UF_HIDDEN`-Flag von `.pth`-Dateien im `.venv` entfernen.
# Idempotent; auf Nicht-macOS ein No-Op. Detaillierte Beschreibung in
# `scripts/_venv_hygiene.py`.
#
# Aufruf:
#   ./scripts/fix-venv-hidden.sh
#
# Sollte nach jedem `uv sync` einmal laufen — alternativ läuft derselbe
# Workaround automatisch als Pytest-Session-Hook (siehe `conftest.py`).

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/_venv_hygiene.py" "$@"
