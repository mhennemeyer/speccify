#!/usr/bin/env bash
#
# fetch_uv.sh — lädt das gepinnte `uv`-Binary als vierten Tauri-Sidecar.
#
# Die App baut ihre Python-Engine mit `uv` (Plan r5-distribution.md, R5.2).
# Ohne mitgeliefertes uv müsste der Nutzer erst `brew install uv` ausführen —
# genau die Repo-/Toolchain-Voraussetzung, die R5 abschaffen soll. Also wandert
# uv wie die MCP-Binaries als `externalBin` ins Bundle und wird beim Signieren
# mit erfasst.
#
# Version ist gepinnt und der Download wird gegen die von astral-sh
# veröffentlichte SHA256 geprüft — ein stiller Austausch fällt auf.
#
# Nutzung:
#   ./scripts/fetch_uv.sh              # holt die gepinnte Version (idempotent)
#   UV_VERSION=0.12.1 ./scripts/fetch_uv.sh
#   ./scripts/fetch_uv.sh --force      # erneut laden, auch wenn vorhanden

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export PATH="/opt/homebrew/opt/rustup/bin:$HOME/.cargo/bin:$PATH"

# Gepinnt: mit dieser Version ist der Engine-Bootstrap verifiziert.
UV_VERSION="${UV_VERSION:-0.12.0}"

FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unbekanntes Argument: $arg" >&2; exit 2 ;;
  esac
done

TRIPLE="$(rustc -vV | awk '/^host: /{print $2}')"
TARGET_DIR="$REPO_ROOT/apps/desktop/src-tauri/binaries"
TARGET="$TARGET_DIR/uv-$TRIPLE"
STAMP="$TARGET_DIR/.uv-version"

if [[ "$FORCE" -eq 0 && -x "$TARGET" && "$(cat "$STAMP" 2>/dev/null || true)" == "$UV_VERSION" ]]; then
  echo "→ uv $UV_VERSION bereits vorhanden ($TARGET)"
  exit 0
fi

ASSET="uv-$TRIPLE.tar.gz"
BASE="https://github.com/astral-sh/uv/releases/download/$UV_VERSION"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "→ uv $UV_VERSION laden ($ASSET)"
curl -fsSL --retry 3 -o "$WORK/$ASSET" "$BASE/$ASSET"
curl -fsSL --retry 3 -o "$WORK/$ASSET.sha256" "$BASE/$ASSET.sha256"

echo "→ SHA256 prüfen"
EXPECTED="$(awk '{print $1}' "$WORK/$ASSET.sha256")"
ACTUAL="$(shasum -a 256 "$WORK/$ASSET" | awk '{print $1}')"
if [[ "$EXPECTED" != "$ACTUAL" ]]; then
  echo "SHA256 stimmt nicht:" >&2
  echo "  erwartet: $EXPECTED" >&2
  echo "  bekommen: $ACTUAL" >&2
  exit 1
fi
echo "  ${ACTUAL:0:16}… ok"

tar -xzf "$WORK/$ASSET" -C "$WORK"
BINARY="$(find "$WORK" -name uv -type f -perm -u+x | head -1)"
if [[ -z "$BINARY" ]]; then
  echo "Kein uv-Binary im Archiv gefunden." >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"
cp -f "$BINARY" "$TARGET"
chmod +x "$TARGET"
printf '%s\n' "$UV_VERSION" >"$STAMP"

# Lizenzhinweis mit ausliefern (uv steht unter MIT/Apache-2.0).
LICENSE_DIR="$REPO_ROOT/apps/desktop/src-tauri/resources/licenses"
mkdir -p "$LICENSE_DIR"
find "$WORK" \( -name "LICENSE*" -o -name "COPYING*" \) -type f -exec cp -f {} "$LICENSE_DIR/" \; 2>/dev/null || true
if ! ls "$LICENSE_DIR"/LICENSE* >/dev/null 2>&1; then
  cat >"$LICENSE_DIR/uv-LICENSE.txt" <<EOF
uv $UV_VERSION — https://github.com/astral-sh/uv
Lizenziert unter MIT ODER Apache-2.0; Volltext siehe Repository.
Als Sidecar in Speccify.app mitgeliefert (scripts/fetch_uv.sh).
EOF
fi

echo "→ uv $UV_VERSION bereit: $TARGET ($(du -h "$TARGET" | cut -f1))"
