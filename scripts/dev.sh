#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -x backend/.venv/bin/python ]; then echo "Create backend/.venv and install requirements first. See README.md."; exit 1; fi
(cd backend && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000) &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT INT TERM
cd frontend
npm run dev -- --hostname 127.0.0.1
