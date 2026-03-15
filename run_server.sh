#!/usr/bin/env bash
# Run the StakeWrap UI server with uvicorn

cd "$(dirname "$0")"

echo "Starting StakeWrap UI server..."
echo "Access at: http://localhost:8000"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

