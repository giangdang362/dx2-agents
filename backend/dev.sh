#!/bin/sh

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  . "$ROOT_DIR/.env"
  set +a
fi

: "${CORS_ALLOW_ORIGIN:=*}"
: "${FORWARDED_ALLOW_IPS:=*}"

PORT="${PORT:-8080}"

while [ $# -gt 0 ]; do
  case "$1" in
    --port)
      PORT="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

: "${WEBUI_URL:=http://localhost:$PORT}"
: "${OPEN_WEBUI_BASE_URL:=http://localhost:$PORT}"
OPEN_WEBUI_BACKEND_PORT="$PORT"
export CORS_ALLOW_ORIGIN WEBUI_URL OPEN_WEBUI_BASE_URL FORWARDED_ALLOW_IPS PORT OPEN_WEBUI_BACKEND_PORT

exec uvicorn open_webui.main:app --port "$PORT" --host 0.0.0.0 --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
