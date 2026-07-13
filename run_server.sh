#!/usr/bin/env bash
# Single entry: start StakeWrap UI with uvicorn (plain HTTP).
#
#   ./run_server.sh
#
# Optional: PORT=8000 HOST=0.0.0.0

set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
PORT="${PORT:-10291}"
HOST="${HOST:-0.0.0.0}"

echo "Starting StakeWrap UI — http://$HOST:$PORT  (UI: http://127.0.0.1:${PORT}/ui )"
echo ""

exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
