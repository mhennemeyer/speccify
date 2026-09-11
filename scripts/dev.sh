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
#   4. Engine-Payload bauen (Wheels + Requirements + Fixtures)
#      — nur wenn er fehlt oder Quellen neuer sind als der Payload
#   5. App starten (tauri dev; mit --release stattdessen .app bauen + öffnen)
#
# Nutzung:
#   ./scripts/dev.sh                # Dev-Modus (Hot Reload, Frontend :1420)
#   ./scripts/dev.sh --release      # .app/.dmg bauen und Speccify.app öffnen
#   ./scripts/dev.sh --refresh      # Payload/Sidecars erzwingen (Caches ignorieren)
#   ./scripts/dev.sh --no-start     # nur vorbereiten, nicht starten
#   ./scripts/dev.sh --skip-engine  # Python-Engine-Payload auslassen (schneller)
#   ./scripts/dev.sh --check        # nur Voraussetzungen prüfen, nichts bauen
#   ./scripts/dev.sh --status       # Listener und lokalen App-Build anzeigen
#   ./scripts/dev.sh --app          # lokale macOS-App ohne Watcher bauen + öffnen
#   ./scripts/dev.sh --open         # vorhandenen lokalen App-Build öffnen
#   ./scripts/dev.sh --ui-port=18768 # expliziter alternativer Fragen-MCP-Port
#   ./scripts/dev.sh --prepared     # vorhandene Deps/Sidecars/Payload verwenden
#
# Für das Web-System (Backend/Playground/Marketing) ist dev-up.sh
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
CHECK_ONLY=0
STATUS_ONLY=0
UI_PORT=8768
PREPARED=0
for arg in "$@"; do
  case "$arg" in
    --release|--bundle) MODE="release" ;;
    --app) MODE="app" ;;
    --open) MODE="open" ;;
    --status) STATUS_ONLY=1 ;;
    --ui-port=*) UI_PORT="${arg#*=}" ;;
    --prepared) PREPARED=1 ;;
    --refresh|--force) REFRESH=1 ;;
    --no-start) START=0 ;;
    --skip-engine) SKIP_ENGINE=1 ;;
    --check) CHECK_ONLY=1 ;;
    -h|--help)
      sed -n '/^#$/,/^set -e/{ /^set -e/d; s/^# \{0,1\}//; p; }' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      echo "Unbekanntes Argument: $arg" >&2
      exit 2
      ;;
  esac
done

source "$REPO_ROOT/scripts/dev-runtime.sh"
if ! command -v lsof >/dev/null 2>&1; then
  echo "lsof fehlt; sichere Portdiagnose ist nicht möglich." >&2
  exit 1
fi
if ! desktop_validate_port "$UI_PORT"; then
  echo "Ungültiger --ui-port: erwartet 1–65535." >&2
  exit 2
fi
UI_PORT=$((10#$UI_PORT))
LOCAL_APP="$REPO_ROOT/target/debug/bundle/macos/Speccify.app"
if [[ "$STATUS_ONLY" -eq 1 ]]; then
  desktop_status "$UI_PORT" "$LOCAL_APP"
  exit 0
fi
if [[ "$MODE" == "app" || "$MODE" == "open" ]] && [[ "$(uname -s)" != "Darwin" ]]; then
  echo "--app/--open ist derzeit ein lokaler macOS-Startweg; Windows: dev.ps1." >&2
  exit 2
fi
if [[ "$MODE" == "open" ]]; then
  if [[ ! -d "$LOCAL_APP" ]]; then
    echo "Noch kein lokaler App-Build. Zuerst: ./scripts/dev.sh --app --ui-port=$UI_PORT" >&2
    exit 1
  fi
  if ! desktop_app_running "$LOCAL_APP"; then
    desktop_require_free_port "$UI_PORT"
  fi
  # Ohne -n: vorhandene Instanz aktivieren, keine zweite erzwingen.
  echo "Öffnen: $LOCAL_APP (Port $UI_PORT gilt nur bei neuem Prozessstart)"
  open "$LOCAL_APP" --args "--desktop-ui-port=$UI_PORT"
  exit 0
fi
if [[ "$MODE" == "app" ]] && desktop_app_running "$LOCAL_APP"; then
  echo "Der lokale App-Build läuft. Mit --open aktivieren; vor Neubau bewusst mit ⌘Q beenden." >&2
  exit 1
fi
if [[ "$START" -eq 1 && "$CHECK_ONLY" -eq 0 ]]; then
  desktop_require_free_port "$UI_PORT"
  if [[ "$MODE" == "dev" ]]; then
    desktop_require_free_port 1420
  fi
fi

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
require node "Node-Version aus .nvmrc installieren (mindestens engines.node aus package.json)"
require pnpm "Corepack verwenden oder die packageManager-Version aus package.json installieren"
require cargo "brew install rustup && rustup default stable"
require rustc "brew install rustup && rustup default stable"
require git "xcode-select --install"
if [[ "$MISSING" -eq 1 ]]; then
  echo "" >&2
  echo "Fehlende Werkzeuge installieren und dev.sh erneut starten." >&2
  exit 1
fi

node -e '
const minimum = require("./package.json").engines.node.replace(/^>=/, "").split(".").map(Number);
const actual = process.versions.node.split(".").map(Number);
let compatible = true;
for (let i = 0; i < 3; i++) {
  if (actual[i] !== minimum[i]) { compatible = actual[i] > minimum[i]; break; }
}
if (!compatible) {
  console.error(`Node ${process.versions.node} ist zu alt. Benötigt: ${require("./package.json").engines.node}; .nvmrc verwenden.`);
  process.exit(1);
}'
PNPM_REQUIRED="$(node -p 'require("./package.json").packageManager.split("@")[1]')"
PNPM_ACTUAL="$(pnpm --version)"
if [[ "$PNPM_ACTUAL" != "$PNPM_REQUIRED" ]]; then
  printf 'pnpm %s benötigt (gefunden: %s). Installation: npm install -g pnpm@%s\n' "$PNPM_REQUIRED" "$PNPM_ACTUAL" "$PNPM_REQUIRED" >&2
  exit 1
fi
skip "Node $(node --version), pnpm $PNPM_ACTUAL, $(uv --version)"
skip "$(rustc --version) — Toolchain aus rust-toolchain.toml"
skip "Python $(tr -d '\n' < .python-version) — wird bei Bedarf durch uv eingerichtet"
if [[ "$(uname -s)" == "Darwin" ]] && ! xcode-select -p >/dev/null 2>&1; then
  echo "Xcode Command Line Tools fehlen: xcode-select --install" >&2
  exit 1
fi
if [[ "$CHECK_ONLY" -eq 1 ]]; then
  step "Voraussetzungen geprüft — keine Abhängigkeiten installiert"
  exit 0
fi

# --- 2. Abhängigkeiten ----------------------------------------------------------

if [[ "$PREPARED" -eq 0 ]]; then
step "JS-Abhängigkeiten (pnpm install)"
pnpm install --frozen-lockfile

step "Python-Abhängigkeiten (uv sync)"
# --all-packages wie in der CI: bringt die .venv exakt auf den Lockfile-Stand.
# Das entfernt auch Pakete, die dort von Hand oder aus entfernten Komponenten
# hängengeblieben sind — gewollt, damit lokal und CI dieselbe Umgebung sehen.
uv sync --frozen --all-packages
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
  uv.lock
  # Die Skill-Bibliothek liegt mit im Payload — ein geänderter Skill muss den
  # Neubau auslösen, sonst zeigt die App die alte Kopie.
  skills
)
if [[ "$SKIP_ENGINE" -eq 1 ]]; then
  step "Engine-Payload"
  skip "übersprungen (--skip-engine)"
elif [[ "$REFRESH" -eq 1 ]] || is_stale "$PAYLOAD" "${ENGINE_SOURCES[@]}"; then
  step "Engine-Payload bauen (Wheels + Requirements)"
  ./scripts/build_engine_payload.sh
else
  step "Engine-Payload"
  skip "aktuell ($(sed -n 's/.*"hash": "\(............\).*/\1/p' "$PAYLOAD")…)"
fi

else
  step "Vorbereitete Umgebung verwenden (--prepared)"
  if [[ ! -d node_modules || ! -d .venv || ! -f "$PAYLOAD" || ! -d "$BINARIES" ]]; then
    echo "Vorbereitung fehlt. Zuerst ./scripts/dev.sh --no-start ausführen." >&2
    exit 1
  fi
  skip "Deps/Sidecars/Payload nicht synchronisiert; nur nach erfolgreicher Vorbereitung verwenden"
fi

# --- 5. Starten -----------------------------------------------------------------

if [[ "$START" -eq 0 ]]; then
  step "Fertig vorbereitet (--no-start)"
  exit 0
fi

if [[ "$MODE" == "app" ]]; then
  step "Lokale App ohne Watcher bauen"
  pnpm --filter speccify-desktop tauri build --debug --bundles app --no-sign
  step "Lokale Speccify.app öffnen (kein Vite/Watcher nötig)"
  echo "  Desktop-UI-MCP: http://127.0.0.1:$UI_PORT"
  open "$LOCAL_APP" --args "--desktop-ui-port=$UI_PORT"
elif [[ "$MODE" == "release" ]]; then
  step "App bündeln (tauri build)"
  pnpm --filter speccify-desktop tauri build
  APP="$REPO_ROOT/target/release/bundle/macos/Speccify.app"
  step "Speccify.app öffnen"
  echo "  $APP"
  open -a "$APP" --args "--desktop-ui-port=$UI_PORT"
else
  step "App starten (tauri dev — Ctrl-C beendet sie)"
  pnpm --filter speccify-desktop tauri dev -- -- "--desktop-ui-port=$UI_PORT"
fi
