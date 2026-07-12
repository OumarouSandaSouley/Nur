#!/usr/bin/env bash
# Lance API + frontend Nur (Git Bash / WSL / macOS / Linux)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ffmpeg dans le PATH utilisateur Windows (si présent)
if [ -d "$LOCALAPPDATA/ffmpeg/ffmpeg-8.0-essentials_build/bin" ]; then
  export PATH="$LOCALAPPDATA/ffmpeg/ffmpeg-8.0-essentials_build/bin:$PATH"
fi

echo "==> Backend http://127.0.0.1:8000"
python run_server.py &
API_PID=$!

echo "==> Frontend http://localhost:5173"
cd frontend
npm run dev &
UI_PID=$!

cleanup() {
  kill "$API_PID" "$UI_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait
