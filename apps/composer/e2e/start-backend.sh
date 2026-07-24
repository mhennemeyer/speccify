#!/usr/bin/env bash
#
# Startet das FastAPI-Backend für den Playwright-Smoke gegen eine
# Wegwerf-Kopie der registry-fixtures — Speichern im Test verschmutzt
# weder specs/ noch registry-fixtures/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PORT="${COMPOSER_E2E_BACKEND_PORT:-8788}"

REG_TMP="$SCRIPT_DIR/.registry-tmp"
rm -rf "$REG_TMP"
cp -R "$REPO_ROOT/registry-fixtures" "$REG_TMP"

export SPECCIFY_REGISTRY_PATH="$REG_TMP"
# macOS-Quarantäne versteckt venv-.pth-Dateien wiederkehrend — PYTHONPATH
# auf die src/-Verzeichnisse umgeht das komplett (harmlos unter Linux/CI).
export PYTHONPATH="$REPO_ROOT/core/src:$REPO_ROOT/cli/src:$REPO_ROOT/mcp/src:$REPO_ROOT/apps/web/backend/src${PYTHONPATH:+:$PYTHONPATH}"

cd "$REPO_ROOT"
exec uv run --no-sync speccify-web-backend --host 127.0.0.1 --port "$PORT"
