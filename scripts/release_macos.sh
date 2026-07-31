#!/usr/bin/env bash
#
# release_macos.sh — signierte, notarisierte Speccify.app + .dmg bauen.
#
# Ablauf (Plan r5-distribution.md, R5.3):
#   1. Preflight: Werkzeuge, Signing-Identity, Notarisierungs-Credentials
#   2. Sidecars (release) + Engine-Payload bauen
#   3. `tauri build` — signiert mit Hardened Runtime, notarisiert bei Apple
#      und stapelt das Ticket ans Bundle (macht die Tauri-CLI selbst)
#   4. Verifikation: codesign, Gatekeeper (spctl), Staple-Ticket
#
# Credentials kommen ausschließlich aus der Umgebung — NIE ins Repo:
#
#   APPLE_SIGNING_IDENTITY   "Developer ID Application: Name (TEAMID)"
#
#   und für die Notarisierung entweder (Apple-ID-Variante)
#     APPLE_ID, APPLE_PASSWORD (App-Specific Password), APPLE_TEAM_ID
#   oder (API-Key-Variante, für CI)
#     APPLE_API_ISSUER, APPLE_API_KEY, APPLE_API_KEY_PATH
#
# Nutzung:
#   ./scripts/release_macos.sh                # voller Lauf
#   ./scripts/release_macos.sh --no-notarize  # nur signieren (schneller Test)
#   ./scripts/release_macos.sh --verify-only  # vorhandenes Bundle nur prüfen
#
# Details, Einrichtung der Credentials und Fehlerbilder: docs/release.md

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export PATH="/opt/homebrew/opt/rustup/bin:$HOME/.cargo/bin:$HOME/.local/bin:/opt/homebrew/bin:$PATH"

NOTARIZE=1
VERIFY_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --no-notarize) NOTARIZE=0 ;;
    --verify-only) VERIFY_ONLY=1 ;;
    -h|--help)
      sed -n '2,27p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unbekanntes Argument: $arg" >&2; exit 2 ;;
  esac
done

APP="$REPO_ROOT/target/release/bundle/macos/Speccify.app"
DMG_DIR="$REPO_ROOT/target/release/bundle/dmg"

step() { printf '\n\033[1m→ %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m⚠\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$1" >&2; }

# --- 1. Preflight ---------------------------------------------------------------

step "Preflight"
PROBLEMS=0

for tool in codesign xcrun spctl; do
  if command -v "$tool" >/dev/null 2>&1; then
    ok "$tool"
  else
    fail "$tool fehlt — Xcode Command Line Tools installieren: xcode-select --install"
    PROBLEMS=$((PROBLEMS + 1))
  fi
done

if [[ "$VERIFY_ONLY" -eq 0 ]]; then
  if [[ -z "${APPLE_SIGNING_IDENTITY:-}" ]]; then
    fail "APPLE_SIGNING_IDENTITY ist nicht gesetzt (siehe docs/release.md)."
    PROBLEMS=$((PROBLEMS + 1))
  else
    # Existiert die Identity wirklich im Keychain? Sonst bricht tauri build
    # erst nach dem kompletten Compile ab.
    if security find-identity -v -p codesigning 2>/dev/null |
        grep -Fq "$APPLE_SIGNING_IDENTITY"; then
      ok "Signing-Identity im Keychain: $APPLE_SIGNING_IDENTITY"
    else
      fail "Identity nicht im Keychain gefunden: $APPLE_SIGNING_IDENTITY"
      printf '    Vorhandene Identities:\n'
      security find-identity -v -p codesigning 2>/dev/null | sed 's/^/      /' || true
      PROBLEMS=$((PROBLEMS + 1))
    fi
    case "$APPLE_SIGNING_IDENTITY" in
      "Developer ID Application:"*) ;;
      *) warn "Für Distribution außerhalb des App Store wird eine „Developer ID Application“-Identity erwartet." ;;
    esac
  fi

  if [[ "$NOTARIZE" -eq 1 ]]; then
    if [[ -n "${APPLE_ID:-}" && -n "${APPLE_PASSWORD:-}" && -n "${APPLE_TEAM_ID:-}" ]]; then
      ok "Notarisierung über Apple ID ($APPLE_ID, Team $APPLE_TEAM_ID)"
    elif [[ -n "${APPLE_API_ISSUER:-}" && -n "${APPLE_API_KEY:-}" && -n "${APPLE_API_KEY_PATH:-}" ]]; then
      ok "Notarisierung über API-Key ($APPLE_API_KEY)"
    else
      fail "Keine Notarisierungs-Credentials — APPLE_ID/APPLE_PASSWORD/APPLE_TEAM_ID"
      printf '    oder APPLE_API_ISSUER/APPLE_API_KEY/APPLE_API_KEY_PATH setzen\n' >&2
      printf '    (oder mit --no-notarize nur signieren).\n' >&2
      PROBLEMS=$((PROBLEMS + 1))
    fi
  else
    warn "--no-notarize: Gatekeeper wird das Ergebnis auf fremden Rechnern blocken."
  fi
fi

if [[ "$PROBLEMS" -gt 0 ]]; then
  echo "" >&2
  echo "Preflight fehlgeschlagen ($PROBLEMS Punkt(e)) — nichts gebaut." >&2
  exit 1
fi

# --- 2./3. Bauen ----------------------------------------------------------------

if [[ "$VERIFY_ONLY" -eq 0 ]]; then
  step "Sidecars + Engine-Payload (release)"
  ./scripts/build_sidecars.sh
  ./scripts/build_engine_payload.sh

  step "tauri build (signieren, notarisieren, stapeln)"
  echo "  Die Notarisierung wartet auf Apple — das dauert typisch 2–15 Minuten."
  if [[ "$NOTARIZE" -eq 0 ]]; then
    # Notarisierungs-Variablen für diesen Lauf ausblenden: dann signiert die
    # Tauri-CLI nur und überspringt notarytool.
    env -u APPLE_ID -u APPLE_PASSWORD -u APPLE_TEAM_ID \
        -u APPLE_API_ISSUER -u APPLE_API_KEY -u APPLE_API_KEY_PATH \
        pnpm --filter speccify-desktop tauri build
  else
    pnpm --filter speccify-desktop tauri build
  fi
fi

if [[ ! -d "$APP" ]]; then
  fail "Kein Bundle unter $APP"
  exit 1
fi

# --- 4. Verifikation ------------------------------------------------------------

step "Signatur prüfen"
VERIFY_PROBLEMS=0
if codesign --verify --deep --strict --verbose=2 "$APP" 2>&1 | sed 's/^/  /'; then
  ok "codesign --verify --deep --strict"
else
  fail "codesign --verify schlägt fehl (unsigniert oder Signatur beschädigt)."
  VERIFY_PROBLEMS=$((VERIFY_PROBLEMS + 1))
fi

codesign -dv --verbose=4 "$APP" 2>&1 |
  grep -E "^(Authority|TeamIdentifier|Identifier|Format|Runtime)" | sed 's/^/  /' || true

# Jedes mitgelieferte Binary einzeln: unsignierte Sidecars lässt die
# Notarisierung durchgehen, Gatekeeper killt sie später beim Start.
step "Sidecars prüfen"
SIDECAR_PROBLEMS=0
for binary in "$APP/Contents/MacOS/"*; do
  name="$(basename "$binary")"
  if codesign --verify --strict "$binary" >/dev/null 2>&1; then
    if codesign -d --verbose=2 "$binary" 2>&1 | grep -q "flags=.*runtime"; then
      ok "$name (signiert, Hardened Runtime)"
    else
      warn "$name signiert, aber ohne Hardened Runtime"
      SIDECAR_PROBLEMS=$((SIDECAR_PROBLEMS + 1))
    fi
  else
    fail "$name ist nicht signiert"
    SIDECAR_PROBLEMS=$((SIDECAR_PROBLEMS + 1))
  fi
done

step "Gatekeeper (spctl)"
if spctl -a -vvv -t exec "$APP" 2>&1 | sed 's/^/  /'; then
  ok "Gatekeeper akzeptiert die App"
else
  fail "Gatekeeper lehnt die App ab — ohne Notarisierung erwartet."
fi

step "Notarisierungs-Ticket (stapler)"
if xcrun stapler validate "$APP" >/dev/null 2>&1; then
  ok "Ticket am .app angeheftet"
else
  warn "Kein Ticket am .app — nicht notarisiert oder Staple fehlgeschlagen."
fi
shopt -s nullglob
for dmg in "$DMG_DIR"/*.dmg; do
  if xcrun stapler validate "$dmg" >/dev/null 2>&1; then
    ok "Ticket am $(basename "$dmg")"
  else
    warn "Kein Ticket am $(basename "$dmg")"
  fi
done

step "Artefakte"
echo "  $APP"
for dmg in "$DMG_DIR"/*.dmg; do
  echo "  $dmg  ($(du -h "$dmg" | cut -f1))"
done

TOTAL=$((VERIFY_PROBLEMS + SIDECAR_PROBLEMS))
if [[ "$TOTAL" -gt 0 ]]; then
  echo "" >&2
  echo "⚠ $TOTAL Signatur-Befund(e) — vor der Veröffentlichung klären (docs/release.md)." >&2
  exit 1
fi
