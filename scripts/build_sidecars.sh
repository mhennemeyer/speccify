#!/usr/bin/env bash
#
# build_sidecars.sh — baut die Rust-MCPs und legt sie als Tauri-Sidecars ab.
#
# Die verteilte Speccify.app darf keine Rust-Toolchain beim Nutzer voraussetzen
# (Plan r5-distribution.md, D1): statt `cargo install --path crates/…` wandern
# die Binaries als `bundle.externalBin` ins App-Bundle (macOS: Contents/MacOS/).
# Tauri erwartet sie unter `<name>-<target-triple>`; die App löst sie zur
# Laufzeit neben ihrem eigenen Binary auf (src-tauri/src/sidecar.rs).
#
# Nutzung:
#   ./scripts/build_sidecars.sh            # release (für tauri build)
#   ./scripts/build_sidecars.sh --debug    # debug (schneller, für tauri dev)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# brew-rustup legt kein ~/.cargo/env an — Skript-PATH selbst anreichern.
export PATH="/opt/homebrew/opt/rustup/bin:$HOME/.cargo/bin:$PATH"

PROFILE="release"
PROFILE_DIR="release"
for arg in "$@"; do
  case "$arg" in
    --debug) PROFILE="dev"; PROFILE_DIR="debug" ;;
    *) echo "Unbekanntes Argument: $arg" >&2; exit 2 ;;
  esac
done

BINARIES=(speccify-exec-mcp speccify-discovery-mcp speccify-parallels-mcp)
TARGET_DIR="$REPO_ROOT/apps/desktop/src-tauri/binaries"
TRIPLE="$(rustc -vV | awk '/^host: /{print $2}')"

if [[ -z "$TRIPLE" ]]; then
  echo "Konnte das Target-Triple nicht ermitteln (rustc -vV)." >&2
  exit 1
fi

echo "→ cargo build --profile $PROFILE ($TRIPLE)"
cargo build --profile "$PROFILE" "${BINARIES[@]/#/--package=}"

mkdir -p "$TARGET_DIR"
for bin in "${BINARIES[@]}"; do
  src="$REPO_ROOT/target/$PROFILE_DIR/$bin"
  dst="$TARGET_DIR/$bin-$TRIPLE"
  if [[ ! -x "$src" ]]; then
    echo "Binary fehlt: $src" >&2
    exit 1
  fi
  cp -f "$src" "$dst"
  echo "  $bin-$TRIPLE"
done

echo "→ Sidecars unter apps/desktop/src-tauri/binaries/ bereit."
