#!/usr/bin/env bash
#
# Starts the FastAPI backend for the Playwright smoke against a throwaway copy
# of the playbook library, so tests never touch the real one.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PORT="${COMPOSER_E2E_BACKEND_PORT:-8788}"

LIB_TMP="$SCRIPT_DIR/.library-tmp"
rm -rf "$LIB_TMP"
cp -R "$REPO_ROOT/skills" "$LIB_TMP"

export SPECCIFY_LIBRARY_PATH="$LIB_TMP"

# Discovery fixture: a real git repository holding a skill, plus an index
# pointing at it — so the UI smoke covers search as well.
GIT_TMP="$SCRIPT_DIR/.git-fixture"
rm -rf "$GIT_TMP"
mkdir -p "$GIT_TMP/button-repo" "$GIT_TMP/index/entries" "$GIT_TMP/git-cache"
cp "$REPO_ROOT/skills/apple-developer-id-cert/SKILL.md" "$GIT_TMP/button-repo/"
git -c init.defaultBranch=main init --quiet "$GIT_TMP/button-repo"
git -C "$GIT_TMP/button-repo" \
  -c user.name="Speccify E2E" -c user.email="e2e@speccify.io" \
  add . >/dev/null
git -C "$GIT_TMP/button-repo" \
  -c user.name="Speccify E2E" -c user.email="e2e@speccify.io" \
  commit --quiet -m "playbook 1.0.0"
git -C "$GIT_TMP/button-repo" tag v1.0.0
cat > "$GIT_TMP/index/entries/cert.yaml" <<YAML
schema_version: 1
source: git+file://$GIT_TMP/button-repo
title: Developer ID certificate (from the index)
summary: Comes from a git repository, not from the local library.
keywords: [codesign, discovery]
YAML

export SPECCIFY_INDEX="$GIT_TMP/index"
export SPECCIFY_GIT_CACHE="$GIT_TMP/git-cache"
# macOS-Quarantäne versteckt venv-.pth-Dateien wiederkehrend — PYTHONPATH
# auf die src/-Verzeichnisse umgeht das komplett (harmlos unter Linux/CI).
export PYTHONPATH="$REPO_ROOT/core/src:$REPO_ROOT/cli/src:$REPO_ROOT/mcp/src:$REPO_ROOT/apps/web/backend/src${PYTHONPATH:+:$PYTHONPATH}"

cd "$REPO_ROOT"
exec uv run --no-sync speccify-web-backend --host 127.0.0.1 --port "$PORT"
