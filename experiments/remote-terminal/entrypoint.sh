#!/bin/sh
# Spec 062 spike: seed a throwaway repo on first start, then serve terminals.
set -eu

if [ ! -d /workspace/demo/.git ]; then
  mkdir -p /workspace/demo
  cd /workspace/demo
  git init -q -b main
  git config user.name "Spike"
  git config user.email "spike@example.invalid"
  printf '# Demo\n\nThrowaway repository for the container terminal spike.\n' > README.md
  git add README.md
  git commit -q -m "chore: seed demo repository"
fi

exec remote-terminal-spike
