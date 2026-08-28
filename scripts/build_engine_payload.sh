#!/usr/bin/env bash
#
# build_engine_payload.sh — packt die Python-Engine als App-Resource.
#
# Die verteilte Speccify.app hat kein Repo und keine `.venv` (Plan
# r5-distribution.md, R5.2/D2). Stattdessen bringt sie mit:
#
#   resources/engine/wheels/*.whl   die vier eigenen Pakete (core/cli/mcp/
#                                   web-backend), gebaut aus diesem Repo
#   resources/engine/requirements.txt  gepinnte Third-Party-Deps (uv export,
#                                   inkl. Hashes — aus uv.lock, reproduzierbar)
#   resources/engine/payload.json   Metadaten + Hash (Marker für Re-Install)
#   resources/skills/               Referenz-Skills (Bibliothek der App)
#
# Beim ersten Start baut die App daraus eine venv unter
# ~/Library/Application Support/io.speccify.desktop/engine/venv (engine.rs).
#
# Nutzung: ./scripts/build_engine_payload.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

RES="$REPO_ROOT/apps/desktop/src-tauri/resources"
ENGINE="$RES/engine"
PACKAGES=(speccify-core speccify-cli speccify-mcp speccify-web-backend)

rm -rf "$ENGINE"
mkdir -p "$ENGINE/wheels"

echo "→ Wheels bauen"
for pkg in "${PACKAGES[@]}"; do
  uv build --package "$pkg" --wheel --out-dir "$ENGINE/wheels" >/dev/null
  echo "  $pkg"
done

echo "→ requirements.txt exportieren (uv.lock, ohne Workspace-Pakete)"
uv export --no-dev --no-emit-workspace --all-packages \
  --format requirements-txt >"$ENGINE/requirements.txt"

rm -rf "$RES/composer" "$RES/skills"
cp -R "$REPO_ROOT/skills" "$RES/skills"

# Hash über alle Payload-Dateien: die App vergleicht ihn mit dem Marker der
# installierten venv und installiert nach einem App-Update neu.
PAYLOAD_HASH="$(
  find "$ENGINE" "$RES/skills" \
    -type f ! -name payload.json | LC_ALL=C sort |
    xargs shasum -a 256 | shasum -a 256 | awk '{print $1}'
)"
PYTHON_VERSION="$(awk -F'"' '/^requires-python/{print $2}' "$REPO_ROOT/pyproject.toml" | tr -d '>=')"

cat >"$ENGINE/payload.json" <<JSON
{
  "hash": "$PAYLOAD_HASH",
  "python": "$PYTHON_VERSION",
  "wheels": [$(ls "$ENGINE/wheels" | sed 's/.*/"&"/' | paste -sd, -)]
}
JSON

echo "→ Payload bereit: $ENGINE (hash ${PAYLOAD_HASH:0:12}…)"
