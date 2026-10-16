#!/usr/bin/env bash
# Starts the API on 5001 and the frontend dev server; Ctrl+C stops both.
set -e
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && source .venv/bin/activate
python -m flask --app backend.app run --port 5001 &
trap 'kill $! 2>/dev/null' EXIT
cd frontend
bun install
bun run dev
