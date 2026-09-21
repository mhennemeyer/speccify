#!/bin/sh
# Spec 062 spike: build and run the container terminal.
#   ./run.sh up        build image, (re)start container, print the URL
#   ./run.sh restart   restart the container only (login and sessions on disk must survive)
#   ./run.sh down      stop and remove the container; volumes stay
#   ./run.sh wipe      remove the container and both volumes (forgets the logins)
#   ./run.sh logs
set -eu
cd "$(dirname "$0")"

NAME=speccify-spike-terminal
IMAGE=speccify-spike-terminal
PORT="${SPIKE_PORT:-8791}"
TOKEN_FILE=.spike-token

token() {
  if [ ! -s "$TOKEN_FILE" ]; then
    (umask 077 && openssl rand -hex 24 > "$TOKEN_FILE")
  fi
  cat "$TOKEN_FILE"
}

case "${1:-up}" in
  up)
    docker build -t "$IMAGE" .
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker run -d --name "$NAME" \
      -p "127.0.0.1:${PORT}:8791" \
      -e SPIKE_TOKEN="$(token)" \
      -e SPIKE_RING_BYTES="${SPIKE_RING_BYTES:-1048576}" \
      -v speccify-spike-home:/home/dev \
      -v speccify-spike-workspace:/workspace \
      "$IMAGE" >/dev/null
    echo "http://localhost:${PORT}/#token=$(token)"
    ;;
  restart) docker restart "$NAME" >/dev/null && echo restarted ;;
  down) docker rm -f "$NAME" >/dev/null && echo removed ;;
  wipe)
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker volume rm speccify-spike-home speccify-spike-workspace
    ;;
  logs) docker logs -f "$NAME" ;;
  token) token ;;
  *) echo "usage: $0 up|restart|down|wipe|logs|token" >&2; exit 2 ;;
esac
