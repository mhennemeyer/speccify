#!/usr/bin/env bash
# Phase-5b-Stage-2-Helper: bündelt alle Schritte für einen
# Bedrock-Replay-Cache-Recording-Lauf in **einem** Aufruf.
#
# Was das Skript tut (idempotent, in dieser Reihenfolge):
#   1. Wechselt ins Repo-Root (Skript-relativ).
#   2. Lädt `.env` (falls vorhanden) für AWS_REGION / AWS_ACCESS_KEY_ID /
#      AWS_SECRET_ACCESS_KEY — ohne die Werte zu loggen.
#   3. `uv sync --extra bedrock` (boto3 + Co. installieren).
#   4. macOS-Quarantäne-Fix: `chflags nohidden` auf alle relevanten
#      `.pth`-Dateien + die editable Workspace-Pakete (vgl. AGENTS.md #6).
#   5. Sanity-Check: editable Imports funktionieren.
#   6. Führt `scripts/record_llm_cache.py` direkt mit dem venv-Python aus
#      (NICHT via `uv run`, das würde die `.pth`-Dateien u. U. wieder
#      verstecken und den ModuleNotFoundError zurückbringen).
#
# Verwendung:
#   ./scripts/record-llm-cache.sh                       # Default: --target all
#   ./scripts/record-llm-cache.sh --target angular,swiftui
#   ./scripts/record-llm-cache.sh --target react --force
#
# Alle Argumente werden 1:1 an `scripts/record_llm_cache.py` durchgereicht.
# Wenn KEIN `--target` übergeben wird, ergänzt das Shell-Skript `--target all`
# (Phase-5b-Default: React + Angular + SwiftUI gemeinsam recorden; vorhandene
# Einträge werden idempotent geskippt). Das Python-Skript selbst behält den
# Phase-1b-Default `react` für Direktaufrufe.

set -euo pipefail

# --- 1. Repo-Root ----------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

echo "==> Repo-Root: ${REPO_ROOT}"

# --- 2. .env laden (ohne Inhalte zu echoen) --------------------------------
if [[ -f .env ]]; then
  echo "==> Lade .env (AWS-Credentials + Region)"
  # Nur AWS_*-Variablen exportieren; Rest der .env bleibt unberührt.
  # `source <(...)` läuft in einer Subshell und verliert Exports — daher
  # zeilenweise lesen und explizit exportieren.
  while IFS='=' read -r key value; do
    # Whitespace + optionale Quotes strippen.
    value="${value%$'\r'}"
    value="${value%\"}"; value="${value#\"}"
    value="${value%\'}"; value="${value#\'}"
    export "${key}=${value}"
  done < <(grep -E '^(AWS_REGION|AWS_DEFAULT_REGION|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN|AWS_PROFILE)=' .env || true)
else
  echo "==> Keine .env gefunden — nutze bereits gesetzte AWS_*-Env-Vars."
fi

if [[ -z "${AWS_REGION:-}${AWS_DEFAULT_REGION:-}" ]]; then
  echo "!! AWS_REGION/AWS_DEFAULT_REGION ist nicht gesetzt." >&2
  exit 2
fi
if [[ -z "${AWS_ACCESS_KEY_ID:-}" && -z "${AWS_PROFILE:-}" ]]; then
  echo "!! Weder AWS_ACCESS_KEY_ID noch AWS_PROFILE gesetzt." >&2
  exit 2
fi

# --- 3. uv sync --extra bedrock -------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  echo "!! 'uv' ist nicht im PATH. Bitte installieren: brew install uv" >&2
  exit 2
fi

echo "==> uv sync --extra bedrock"
uv sync --extra bedrock

# --- 4. macOS-Quarantäne-Fix (idempotent) ----------------------------------
VENV_SITE=".venv/lib/python3.12/site-packages"
if [[ -d "${VENV_SITE}" ]]; then
  echo "==> chflags nohidden auf .pth + Workspace-Pakete"
  # `chflags` ist macOS-spezifisch; auf Linux einfach skippen.
  if command -v chflags >/dev/null 2>&1; then
    # `|| true`, weil bei Linux/anderen FS chflags fehlschlägt — egal.
    chflags nohidden "${VENV_SITE}"/*.pth 2>/dev/null || true
    for pkg in speccify_core speccify_cli speccify_mcp; do
      # Sowohl Verzeichnis als auch dist-info ent-verstecken (rekursiv).
      chflags -R nohidden "${VENV_SITE}/${pkg}"* 2>/dev/null || true
    done
  fi
fi

PY=".venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  echo "!! ${PY} nicht gefunden — uv sync hat das venv nicht angelegt?" >&2
  exit 2
fi

# --- 5. Sanity-Check (kein Netz) ------------------------------------------
echo "==> Sanity-Check: editable Imports"
"${PY}" - <<'PYEOF'
from speccify_core.codegen import angular_llm, swiftui_llm, react_llm  # noqa: F401
print("ok: speccify_core editable import funktioniert")
PYEOF

# --- 6. Recording-Lauf -----------------------------------------------------
# Default-Target = `all` (Phase-5b-Workflow), außer der Aufrufer hat selbst
# `--target ...` gesetzt.
HAS_TARGET=0
for arg in "$@"; do
  if [[ "${arg}" == "--target" || "${arg}" == --target=* ]]; then
    HAS_TARGET=1
    break
  fi
done

if [[ "${HAS_TARGET}" -eq 0 ]]; then
  set -- --target all "$@"
  echo "==> Kein --target übergeben → Default: --target all"
fi

echo "==> Starte Recording (Argumente: $*)"
exec "${PY}" scripts/record_llm_cache.py "$@"
