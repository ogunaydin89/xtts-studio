#!/usr/bin/env bash
# ==============================================================================
# XTTS Studio - Standalone Desktop Launcher with Auto-Shutdown
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=5222
CHROME_PROFILE="/home/helin/.cache/xtts-studio-chrome"

echo "🎙️ Initializing XTTS Studio..."

# 0. Clean shutdown handler
cleanup() {
    echo ""
    echo "🛑 Shutting down XTTS Studio..."
    if [ -n "${SERVER_PID:-}" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    pkill -f "xtts-studio/app.py" 2>/dev/null || true
    echo "✨ XTTS Studio closed. Zero background footprint."
}
trap cleanup EXIT INT TERM

# 1. Check if XTTS Studio server is running
if ! curl -s "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>&1; then
    echo "🚀 Launching XTTS Studio server on http://127.0.0.1:${PORT}..."
    python3 "$SCRIPT_DIR/app.py" &
    SERVER_PID=$!
    sleep 0.8
else
    SERVER_PID=""
fi

# 2. Open UI in isolated native Qt6 window (or fallback to Chrome/browser)
URL="http://127.0.0.1:${PORT}"
WINDOW_RUNNER="$SCRIPT_DIR/window.py"

if [ -f "$WINDOW_RUNNER" ] && [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
    echo "🖥️ Running XTTS Studio in native isolated Qt6 window..."
    "$SCRIPT_DIR/.venv/bin/python" "$WINDOW_RUNNER" "$URL" "XTTS Studio" "$SCRIPT_DIR/icon.svg"
elif [ -x "/opt/google/chrome/google-chrome" ]; then
    echo "🖥️ Running XTTS Studio (closing window will shut down server)..."
    mkdir -p "$CHROME_PROFILE"
    /opt/google/chrome/google-chrome \
        --user-data-dir="$CHROME_PROFILE" \
        --app="$URL" \
        --no-first-run \
        --disable-default-apps \
        --disable-sync \
        "$@"
elif command -v xdg-open >/dev/null 2>&1; then
    echo "🖥️ Opening in default browser..."
    xdg-open "$URL"
    echo "Press Enter or Ctrl+C to shut down..."
    read -r
else
    echo "Please open $URL in your web browser."
    echo "Press Enter or Ctrl+C to shut down..."
    read -r
fi
