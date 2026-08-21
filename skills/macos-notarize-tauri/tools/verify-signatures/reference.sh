#!/usr/bin/env bash
# Verify the bundle and every embedded binary. Notarization fails on unsigned
# sidecars, and the build itself will not tell you.
set -euo pipefail

APP="${1:?usage: verify-signatures.sh <path to .app>}"

codesign --verify --deep --strict --verbose=2 "$APP"

find "$APP/Contents/MacOS" -type f -perm -u+x | while read -r binary; do
  printf '%s: ' "$(basename "$binary")"
  codesign --verify --strict "$binary" && echo "ok"
done
