#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000