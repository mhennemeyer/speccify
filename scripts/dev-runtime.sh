#!/usr/bin/env bash
# Read-only local startup diagnostics, sourced by dev.sh.

desktop_listener() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null || true
}

desktop_status() {
  local port="$1" app="$2" listener
  printf 'Desktop-UI-MCP: http://127.0.0.1:%s\n' "$port"
  listener="$(desktop_listener "$port")"
  if [[ -n "$listener" ]]; then
    printf '%s\n' "$listener"
  else
    printf 'Kein Listener auf Port %s.\n' "$port"
  fi
  listener="$(desktop_listener 1420)"
  if [[ -n "$listener" ]]; then
    printf 'Frontend-Port 1420:\n%s\n' "$listener"
  else
    printf 'Kein Dev-Frontend auf Port 1420.\n'
  fi
  if [[ -d "$app" ]]; then
    printf 'Lokaler App-Build: %s\n' "$app"
  else
    printf 'Noch kein lokaler App-Build: %s\n' "$app"
  fi
}

desktop_require_free_port() {
  local port="$1" listener
  listener="$(desktop_listener "$port")"
  [[ -z "$listener" ]] && return 0
  printf 'Port %s ist belegt; das beweist keine laufende Speccify-App.\n%s\n' "$port" "$listener" >&2
  printf 'Kein Prozess wurde beendet. Für die App einen freien --ui-port=<Port> wählen.\n' >&2
  printf 'Eine bereits laufende lokale App mit --open wieder in den Vordergrund holen.\n' >&2
  return 1
}

desktop_validate_port() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [[ ${#1} -le 5 ]] && (( 10#$1 >= 1 && 10#$1 <= 65535 ))
}
