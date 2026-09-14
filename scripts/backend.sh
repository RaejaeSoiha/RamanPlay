#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python="$root/backend/.venv/bin/python"

if [ ! -x "$python" ]; then
  echo "RamanPlay backend dependencies are missing." >&2
  echo "Create the virtual environment and install requirements:" >&2
  echo "  cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi

if ! "$python" -c 'import apscheduler, fastapi, httpx, pydantic_settings, sqlalchemy, uvicorn' >/dev/null 2>&1; then
  echo "RamanPlay backend dependencies are incomplete." >&2
  echo "Install them with:" >&2
  echo "  cd backend && .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi

cd "$root/backend"
exec "$python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
