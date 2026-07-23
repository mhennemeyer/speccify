#!/usr/bin/env bash
#
# dev-up.sh — startet das komplette Speccify-System lokal für End-to-End-Dogfooding.
#
# Hochgefahren werden (jeweils im Vordergrund dieses Skripts als Hintergrund-Job,
# mit Präfix-Logs und gemeinsamem Shutdown via Ctrl-C):
#
#   * Playground-Backend (FastAPI)  http://127.0.0.1:8000   speccify-web-backend + Composer-API
#   * Composer (Vite-SPA)           http://localhost:5173   Visueller Composer
#   * Playground-Frontend (Next.js) http://localhost:3000   Monaco-Editor-Spielwiese
#   * Marketing/Doku (Astro)        http://localhost:4321   Landingpage + Doku
#
# Nutzung:
#   ./scripts/dev-up.sh                 # alles starten
#   ./scripts/dev-up.sh --no-frontends  # nur Playground-Backend (kein pnpm/Node)
#
# Voraussetzungen: `uv sync` einmal gelaufen; für die Frontends `pnpm` installiert.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RUN_FRONTENDS=1
for arg in "$@"; do
  case "$arg" in
    --no-frontends) RUN_FRONTENDS=0 ;;
    -h|--help)
      sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unbekanntes Argument: $arg" >&2
      exit 2
      ;;
  esac
done

BACKEND_PORT=8000
COMPOSER_PORT=5173
FRONTEND_PORT=3000
MARKETING_PORT=4321

PIDS=()
_CLEANED=0

cleanup() {
  # Nur einmal aufräumen, auch wenn EXIT+INT/TERM zusammenfallen.
  [[ "$_CLEANED" -eq 1 ]] && return
  _CLEANED=1
  echo ""
  echo "→ Stoppe alle Dev-Services …"
  # Ganze Prozessgruppe beenden (Kindprozesse von pnpm/uv inklusive).
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Präfix-Logger: liest stdin und stellt jeder Zeile ein farbiges Label voran.
prefix() {
  local label="$1"
  while IFS= read -r line; do
    printf '[%s] %s\n' "$label" "$line"
  done
}

echo "→ macOS-Venv-Hygiene (entversteckt .pth-Dateien) …"
if [[ -x ./scripts/fix-venv-hidden.sh ]]; then
  ./scripts/fix-venv-hidden.sh --deep >/dev/null 2>&1 || true
fi

# Wichtig: `uv run` würde sonst bei jedem Aufruf neu syncen und dabei (macOS-
# Quarantäne) die editable-`.pth`-Dateien erneut verstecken. Nach der
# einmaligen Hygiene oben deaktivieren wir das Re-Sync für alle folgenden
# `uv run`-Aufrufe.
export UV_NO_SYNC=1

echo "→ Starte Services (Ctrl-C beendet alle) …"

# Playground-Backend (FastAPI, in-process speccify-core).
( trap - EXIT INT TERM; uv run speccify-web-backend --host 127.0.0.1 --port "${BACKEND_PORT}" 2>&1 | prefix backend ) &
PIDS+=($!)

if [[ "$RUN_FRONTENDS" -eq 1 ]]; then
  echo "→ pnpm install (Workspace) …"
  pnpm install 2>&1 | prefix pnpm

  # Composer (Vite-SPA, proxied /api → Backend).
  ( trap - EXIT INT TERM; pnpm run composer:dev 2>&1 | prefix composer ) &
  PIDS+=($!)

  # Playground-Frontend (Next.js).
  ( trap - EXIT INT TERM; cd apps/web/frontend && pnpm dev 2>&1 | prefix frontend ) &
  PIDS+=($!)

  # Marketing/Doku (Astro) — Iframe zeigt auf das lokale Playground-Frontend.
  ( trap - EXIT INT TERM; PUBLIC_PLAYGROUND_URL="http://localhost:${FRONTEND_PORT}" pnpm run marketing:dev 2>&1 | prefix marketing ) &
  PIDS+=($!)
fi

cat <<EOF

────────────────────────────────────────────────────────────
  Speccify läuft lokal:

    Playground-Backend (API)  : http://127.0.0.1:${BACKEND_PORT}
EOF
if [[ "$RUN_FRONTENDS" -eq 1 ]]; then
cat <<EOF
    Composer (visuell)        : http://localhost:${COMPOSER_PORT}
    Playground-Frontend       : http://localhost:${FRONTEND_PORT}
    Marketing/Doku            : http://localhost:${MARKETING_PORT}
EOF
fi
cat <<EOF

  Ctrl-C beendet alle Services.
  Walkthrough: docs/local-dev-e2e.md
────────────────────────────────────────────────────────────

EOF

# Auf alle Hintergrund-Jobs warten; bricht einer ab, räumt das EXIT-Trap auf.
wait
