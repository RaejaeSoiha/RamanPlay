#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if [ ! -x "$root/frontend/node_modules/.bin/next" ]; then
  echo "RamanPlay frontend dependencies are missing." >&2
  echo "Install them with:" >&2
  echo "  cd frontend && npm install" >&2
  exit 1
fi

exec npm --prefix "$root/frontend" run dev -- --hostname 127.0.0.1
