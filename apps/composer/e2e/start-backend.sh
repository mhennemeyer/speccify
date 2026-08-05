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

# Discovery-Fixture (P5): ein echtes Git-Repo mit der Button-Spec plus ein
# Index, der darauf zeigt. Damit deckt der UI-Smoke den ganzen Weg ab —
# Index-Suche → Git-Quelle als Kind → Mock im Canvas.
GIT_TMP="$SCRIPT_DIR/.git-fixture"
rm -rf "$GIT_TMP"
mkdir -p "$GIT_TMP/button-repo" "$GIT_TMP/index/entries" "$GIT_TMP/git-cache"
cp "$REPO_ROOT/registry-fixtures/org/button/0.1.0/spec.speccify.yaml" "$GIT_TMP/button-repo/"
git -c init.defaultBranch=main init --quiet "$GIT_TMP/button-repo"
git -C "$GIT_TMP/button-repo" \
  -c user.name="Speccify E2E" -c user.email="e2e@speccify.io" \
  add . >/dev/null
git -C "$GIT_TMP/button-repo" \
  -c user.name="Speccify E2E" -c user.email="e2e@speccify.io" \
  commit --quiet -m "button 0.1.0"
git -C "$GIT_TMP/button-repo" tag v0.1.0
cat > "$GIT_TMP/index/entries/button.yaml" <<YAML
schema_version: 1
source: git+file://$GIT_TMP/button-repo
title: Button aus dem Index
summary: Knopf mit Varianten — kommt aus einem Git-Repo, nicht aus der Registry.
kind: ui-component
keywords: [button, discovery]
YAML

export SPECCIFY_INDEX="$GIT_TMP/index"
export SPECCIFY_GIT_CACHE="$GIT_TMP/git-cache"
# macOS-Quarantäne versteckt venv-.pth-Dateien wiederkehrend — PYTHONPATH
# auf die src/-Verzeichnisse umgeht das komplett (harmlos unter Linux/CI).
export PYTHONPATH="$REPO_ROOT/core/src:$REPO_ROOT/cli/src:$REPO_ROOT/mcp/src:$REPO_ROOT/apps/web/backend/src${PYTHONPATH:+:$PYTHONPATH}"

cd "$REPO_ROOT"
exec uv run --no-sync speccify-web-backend --host 127.0.0.1 --port "$PORT"
