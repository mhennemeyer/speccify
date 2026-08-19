#!/usr/bin/env bash
#
# dev.sh — Speccify-Desktop-App bauen und starten, idempotent.
#
# Macht in einem Rutsch alles, was die App braucht, und überspringt jeden
# Schritt, der schon erledigt ist:
#
#   1. Werkzeuge prüfen (uv, pnpm, cargo) — mit Installations-Hinweis
#   2. Abhängigkeiten laden (pnpm install, uv sync + macOS-Venv-Hygiene)
#   3. Sidecars bauen (exec/discovery/parallels-mcp → src-tauri/binaries/)
#   4. Engine-Payload bauen (Wheels + Requirements + Composer-SPA + Fixtures)
#      — nur wenn er fehlt oder Quellen neuer sind als der Payload
#   5. App starten (tauri dev; mit --release stattdessen .app bauen + öffnen)
#
# Nutzung:
#   ./scripts/dev.sh                # Dev-Modus (Hot Reload, Frontend :1420)
#   ./scripts/dev.sh --release      # .app/.dmg bauen und Speccify.app öffnen
#   ./scripts/dev.sh --refresh      # Payload/Sidecars erzwingen (Caches ignorieren)
#   ./scripts/dev.sh --no-start     # nur vorbereiten, nicht starten
#   ./scripts/dev.sh --skip-engine  # Python-Engine-Payload auslassen (schneller)
#
# Für das Web-System (Backend/Composer/Playground/Marketing) ist dev-up.sh
# zuständig — dieses Skript kümmert sich um die Desktop-App.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# GUI-/Skript-PATH anreichern: brew-rustup legt kein ~/.cargo/env an, und uv
# liegt je nach Installationsweg in ~/.local/bin.
export PATH="/opt/homebrew/opt/rustup/bin:$HOME/.cargo/bin:$HOME/.local/bin:/opt/homebrew/bin:$PATH"

MODE="dev"
REFRESH=0
START=1
SKIP_ENGINE=0
for arg in "$@"; do
  case "$arg" in
    --release|--bundle) MODE="release" ;;
    --refresh|--force) REFRESH=1 ;;
    --no-start) START=0 ;;
    --skip-engine) SKIP_ENGINE=1 ;;
    -h|--help)
      sed -n '2,23p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unbekanntes Argument: $arg" >&2
      exit 2
      ;;
  esac
done

step() { printf '\n\033[1m→ %s\033[0m\n' "$1"; }
skip() { printf '  \033[2m✓ %s\033[0m\n' "$1"; }

RESOURCES="$REPO_ROOT/apps/desktop/src-tauri/resources"
BINARIES="$REPO_ROOT/apps/desktop/src-tauri/binaries"
PAYLOAD="$RESOURCES/engine/payload.json"

# Ist `marker` älter als irgendeine Datei unter den angegebenen Pfaden?
# (fehlender Marker ⇒ ja). Bewusst nur auf Quellverzeichnisse angewandt,
# damit node_modules/target/dist keine Fehlalarme auslösen.
is_stale() {
  local marker="$1"
  shift
  [[ -e "$marker" ]] || return 0
  local path
  for path in "$@"; do
    [[ -e "$path" ]] || continue
    if [[ -n "$(find "$path" -type f -newer "$marker" -print -quit 2>/dev/null)" ]]; then
      return 0
    fi
  done
  return 1
}

# --- 1. Werkzeuge ---------------------------------------------------------------

step "Werkzeuge prüfen"
MISSING=0
require() {
  local binary="$1" hint="$2"
  if command -v "$binary" >/dev/null 2>&1; then
    skip "$binary — $(command -v "$binary")"
  else
    printf '  \033[31m✗ %s fehlt\033[0m — Installation: %s\n' "$binary" "$hint" >&2
    MISSING=1
  fi
}
require uv "brew install uv"
require pnpm "brew install pnpm"
require cargo "brew install rustup && rustup default stable"
if [[ "$MISSING" -eq 1 ]]; then
  echo "" >&2
  echo "Fehlende Werkzeuge installieren und dev.sh erneut starten." >&2
  exit 1
fi

# --- 2. Abhängigkeiten ----------------------------------------------------------

step "JS-Abhängigkeiten (pnpm install)"
pnpm install

step "Python-Abhängigkeiten (uv sync)"
# --all-packages wie in der CI: bringt die .venv exakt auf den Lockfile-Stand.
# Das entfernt auch Pakete, die dort von Hand oder aus entfernten Komponenten
# hängengeblieben sind — gewollt, damit lokal und CI dieselbe Umgebung sehen.
uv sync --all-packages
# macOS-Quarantäne versteckt die editable-.pth-Dateien der venv wiederkehrend.
if [[ -x ./scripts/fix-venv-hidden.sh ]]; then
  ./scripts/fix-venv-hidden.sh --deep >/dev/null 2>&1 || true
fi

# `dist-info` ohne `RECORD` kann uv nicht deinstallieren — es meldet die
# Pakete bei JEDEM Sync erneut als entfernt. Typische Altlast ausgebauter
# Komponenten; nur ein frischer venv-Aufbau räumt das wirklich auf.
BROKEN=0
for info in .venv/lib/python*/site-packages/*.dist-info; do
  [[ -d "$info" && ! -f "$info/RECORD" ]] && BROKEN=$((BROKEN + 1))
done
if [[ "$BROKEN" -gt 0 ]]; then
  printf '  \033[33m⚠ %s Paket-Metadaten in .venv ohne RECORD\033[0m — uv meldet sie bei jedem Sync.\n' "$BROKEN"
  printf '    Aufräumen (dauert einen Moment): rm -rf .venv && ./scripts/dev.sh --no-start\n'
fi

# --- 3. Sidecars ----------------------------------------------------------------

TRIPLE="$(rustc -vV | awk '/^host: /{print $2}')"
SIDECAR_MARKER="$BINARIES/speccify-exec-mcp-$TRIPLE"
if [[ "$REFRESH" -eq 1 ]] || is_stale "$SIDECAR_MARKER" crates Cargo.toml Cargo.lock; then
  step "MCP-Sidecars bauen"
  if [[ "$MODE" == "release" ]]; then
    ./scripts/build_sidecars.sh
  else
    ./scripts/build_sidecars.sh --debug
  fi
else
  step "MCP-Sidecars"
  skip "aktuell ($TRIPLE)"
fi

# --- 4. Engine-Payload ----------------------------------------------------------

ENGINE_SOURCES=(
  core/src cli/src mcp/src apps/web/backend/src
  apps/composer/src apps/composer/index.html apps/composer/package.json
  uv.lock
  # Die Skill-Bibliothek liegt mit im Payload — ein geänderter Skill muss den
  # Neubau auslösen, sonst zeigt die App die alte Kopie.
  skills
)
if [[ "$SKIP_ENGINE" -eq 1 ]]; then
  step "Engine-Payload"
  skip "übersprungen (--skip-engine)"
elif [[ "$REFRESH" -eq 1 ]] || is_stale "$PAYLOAD" "${ENGINE_SOURCES[@]}"; then
  step "Engine-Payload bauen (Wheels + Requirements + Composer-SPA)"
  ./scripts/build_engine_payload.sh
else
  step "Engine-Payload"
  skip "aktuell ($(sed -n 's/.*"hash": "\(............\).*/\1/p' "$PAYLOAD")…)"
fi

# --- 5. Starten -----------------------------------------------------------------

if [[ "$START" -eq 0 ]]; then
  step "Fertig vorbereitet (--no-start)"
  exit 0
fi

# Die App hält den desktop-ui-MCP auf :8768 und ist Single-Instance — eine
# zweite Instanz würde sich nur ins Leere starten.
if lsof -ti :8768 >/dev/null 2>&1; then
  echo "" >&2
  echo "⚠ Auf :8768 läuft bereits eine Speccify-Instanz (desktop-ui-MCP)." >&2
  echo "  Erst beenden (⌘Q oder: pkill -f 'Speccify.app|speccify-desktop'), dann erneut starten." >&2
  exit 1
fi

if [[ "$MODE" == "release" ]]; then
  step "App bündeln (tauri build)"
  pnpm --filter speccify-desktop tauri build
  APP="$REPO_ROOT/target/release/bundle/macos/Speccify.app"
  step "Speccify.app öffnen"
  echo "  $APP"
  open -a "$APP"
else
  step "App starten (tauri dev — Ctrl-C beendet sie)"
  pnpm --filter speccify-desktop tauri dev
fi
