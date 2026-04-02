export CORS_ALLOW_ORIGIN="*"
export WEBUI_URL="http://localhost:5173"
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

uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload
