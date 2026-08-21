#!/usr/bin/env bash
#
# Smoke-test a local exec helper: streaming, termination, kill-on-disconnect
# and the two local-server guard rails.
#
# Usage: ./verify-stream.sh [base-url] [project-root]
#   ./verify-stream.sh http://127.0.0.1:8765 "$PWD"
#
# Exits non-zero on the first failure. Everything here is deliberately curl +
# shell: it tests the wire, not your client.

set -uo pipefail

BASE="${1:-http://127.0.0.1:8765}"
PROJECT="${2:-$PWD}"
PORT="${BASE##*:}"; PORT="${PORT%%/*}"
fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "ok   $*"; }

# --- 1. bound to loopback only -------------------------------------------------
if command -v lsof >/dev/null; then
  listen="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
  [ -n "$listen" ] || fail "nothing listening on port $PORT"
  grep -q '\*:' <<<"$listen" && fail "server listens on all interfaces (0.0.0.0) — bind to 127.0.0.1"
  ok "listening on loopback only"
fi

# --- 2. foreign Origin is rejected ---------------------------------------------
status="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/mcp" \
  -H 'Content-Type: application/json' \
  -H 'Origin: https://evil.example' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}')"
if [ "$status" = "200" ]; then
  fail "a request with Origin: https://evil.example was accepted (DNS-rebinding hole)"
fi
ok "foreign Origin rejected (HTTP $status)"

# --- 3. streaming: lines arrive before the end ---------------------------------
tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
curl -sN -X POST "$BASE/stream" -H 'Content-Type: application/json' \
  -d "{\"command\":\"sh -c 'echo one; sleep 1; echo two'\",\"project\":\"$PROJECT\"}" \
  >"$tmp" 2>/dev/null &
curl_pid=$!
sleep 0.5
grep -q '"type":"line"' "$tmp" \
  || fail "no line event within 500ms — output is buffered, not streamed"
ok "first line arrives while the command is still running"
wait "$curl_pid" 2>/dev/null || true
grep -q '"type":"exit"' "$tmp" || fail "stream ended without a terminal exit event"
ok "terminal exit event present"

# --- 4. a failure before execution still terminates the stream -----------------
out="$(curl -sN -X POST "$BASE/stream" -H 'Content-Type: application/json' \
  -d "{\"command\":\"definitely-not-a-real-binary\",\"project\":\"$PROJECT\"}" 2>/dev/null)"
grep -q '"type":"exit"' <<<"$out" \
  || fail "a command that cannot start produced no exit event — clients would wait forever"
ok "pre-execution failure still ends with an exit event"

# --- 5. disconnect kills the child ---------------------------------------------
marker="exec-smoke-$$"
curl -sN -X POST "$BASE/stream" -H 'Content-Type: application/json' \
  -d "{\"command\":\"sh -c 'sleep 120 # $marker'\",\"project\":\"$PROJECT\"}" \
  >/dev/null 2>&1 &
curl_pid=$!
sleep 1
kill "$curl_pid" 2>/dev/null || true      # client disconnects
sleep 1
if pgrep -f "$marker" >/dev/null; then
  pkill -f "$marker" 2>/dev/null || true
  fail "child survived the client disconnect — the stop button will not stop anything"
fi
ok "disconnect killed the child process"

echo "all checks passed"
