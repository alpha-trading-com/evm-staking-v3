#!/usr/bin/env bash
# Run the StakeWrap UI server with uvicorn
#
# HTTP (default):
#   ./run_server.sh
#
# HTTPS (TLS in uvicorn) — set cert + key PEM paths:
#   export UVICORN_SSL_CERTFILE=/path/to/fullchain.pem
#   export UVICORN_SSL_KEYFILE=/path/to/privkey.pem
#   ./run_server.sh
#
# Self-signed for local / testing (browsers will warn until you trust the cert):
#   openssl req -x509 -newkey rsa:4096 -nodes -keyout ssl/key.pem -out ssl/cert.pem \
#     -days 365 -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
#   export UVICORN_SSL_CERTFILE=$PWD/ssl/cert.pem UVICORN_SSL_KEYFILE=$PWD/ssl/key.pem
#   ./run_server.sh
#
# Production on a public IP/domain: prefer Caddy or nginx on :443 with Let's Encrypt,
# proxy_pass to uvicorn on 127.0.0.1:19000 (HTTP). No code change needed in the app.

cd "$(dirname "$0")"

PORT="${PORT:-19000}"
HOST="${HOST:-0.0.0.0}"

SSL_ARGS=()
if [[ -n "${UVICORN_SSL_CERTFILE:-}" && -n "${UVICORN_SSL_KEYFILE:-}" ]]; then
  if [[ ! -f "$UVICORN_SSL_CERTFILE" || ! -f "$UVICORN_SSL_KEYFILE" ]]; then
    echo "ERROR: UVICORN_SSL_CERTFILE / UVICORN_SSL_KEYFILE must be readable files." >&2
    exit 1
  fi
  SSL_ARGS=(--ssl-certfile "$UVICORN_SSL_CERTFILE" --ssl-keyfile "$UVICORN_SSL_KEYFILE")
  SCHEME="https"
else
  SCHEME="http"
fi

echo "Starting StakeWrap UI server ($SCHEME)..."
echo "Bind: $HOST:$PORT  →  open ${SCHEME}://127.0.0.1:${PORT}/ui"
echo ""

exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload "${SSL_ARGS[@]}"
