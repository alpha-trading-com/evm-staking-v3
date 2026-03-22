#!/usr/bin/env bash
# Single entry: start StakeWrap UI with uvicorn.
#
# Default: HTTPS using ./ssl/cert.pem + ./ssl/key.pem (creates self-signed certs if missing).
#   ./run_server.sh
#
# Plain HTTP (no TLS):
#   USE_HTTP=1 ./run_server.sh
#
# Your own cert (e.g. Let's Encrypt):
#   UVICORN_SSL_CERTFILE=/path/fullchain.pem UVICORN_SSL_KEYFILE=/path/privkey.pem ./run_server.sh
#
# Extra SANs for the auto-generated cert (comma-separated, OpenSSL subjectAltName syntax):
#   TLS_SAN_EXTRA=IP:203.0.113.1,DNS:stake.example.com ./run_server.sh
#
# Optional: PORT=8000 HOST=0.0.0.0

set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
PORT="${PORT:-19000}"
HOST="${HOST:-0.0.0.0}"
SSL_DIR="$ROOT/ssl"
CERT="$SSL_DIR/cert.pem"
KEY="$SSL_DIR/key.pem"

SSL_ARGS=()
SCHEME="http"

if [[ "${USE_HTTP:-0}" == "1" ]]; then
  :
elif [[ -n "${UVICORN_SSL_CERTFILE:-}" && -n "${UVICORN_SSL_KEYFILE:-}" ]]; then
  if [[ ! -f "$UVICORN_SSL_CERTFILE" || ! -f "$UVICORN_SSL_KEYFILE" ]]; then
    echo "ERROR: UVICORN_SSL_CERTFILE / UVICORN_SSL_KEYFILE must exist." >&2
    exit 1
  fi
  SSL_ARGS=(--ssl-certfile "$UVICORN_SSL_CERTFILE" --ssl-keyfile "$UVICORN_SSL_KEYFILE")
  SCHEME="https"
else
  mkdir -p "$SSL_DIR"
  if [[ ! -f "$CERT" || ! -f "$KEY" ]]; then
    echo "Generating self-signed TLS cert in $SSL_DIR (first run)..."
    SAN="DNS:localhost,IP:127.0.0.1"
    if [[ -n "${TLS_SAN_EXTRA:-}" ]]; then
      SAN="$SAN,$TLS_SAN_EXTRA"
    fi
    # First non-loopback IPv4 on this machine (helps LAN access; add TLS_SAN_EXTRA for public IP/DNS)
    PUB_IP=""
    if command -v hostname >/dev/null 2>&1; then
      PUB_IP=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^127\.' | grep -v '^$' | head -1 || true)
    fi
    if [[ -n "$PUB_IP" ]]; then
      SAN="$SAN,IP:$PUB_IP"
    fi
    openssl req -x509 -newkey rsa:4096 -nodes \
      -keyout "$KEY" -out "$CERT" -days 825 \
      -subj "/CN=localhost" \
      -addext "subjectAltName=$SAN"
    chmod 600 "$KEY" 2>/dev/null || true
    echo "Done. Browsers will warn until you trust this cert (or use a real CA via UVICORN_SSL_*)."
  fi
  SSL_ARGS=(--ssl-certfile "$CERT" --ssl-keyfile "$KEY")
  SCHEME="https"
fi

echo "Starting StakeWrap UI — $SCHEME://$HOST:$PORT  (UI: ${SCHEME}://127.0.0.1:${PORT}/ui )"
echo ""

exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload "${SSL_ARGS[@]}"
