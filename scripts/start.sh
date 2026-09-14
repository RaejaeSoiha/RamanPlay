#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
backend_pid=""
frontend_pid=""

cleanup() {
  trap - EXIT INT TERM
  [ -z "$frontend_pid" ] || kill -TERM "$frontend_pid" 2>/dev/null || true
  [ -z "$backend_pid" ] || kill -TERM "$backend_pid" 2>/dev/null || true
  [ -z "$frontend_pid" ] || wait "$frontend_pid" 2>/dev/null || true
  [ -z "$backend_pid" ] || wait "$backend_pid" 2>/dev/null || true
}

trap 'cleanup; exit 130' INT TERM
trap cleanup EXIT

sh "$root/scripts/backend.sh" &
backend_pid=$!
sh "$root/scripts/frontend.sh" &
frontend_pid=$!

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

wait "$backend_pid" || true
wait "$frontend_pid" || true
exit 1
