#!/bin/bash
# One-command setup + start for Mashup Maker on macOS.
#
#   ./run-mac.sh                 set up (first run) and start the server
#   ./run-mac.sh --install-autostart   also start automatically at login (launchd)
#   ./run-mac.sh --remove-autostart    undo the above
#
# After it starts, open the printed URL on your phone (same WiFi network).

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

PORT="${PORT:-5000}"
PLIST="$HOME/Library/LaunchAgents/com.mashupmaker.app.plist"

# ---------------------------------------------------------------- autostart
if [ "$1" = "--remove-autostart" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "Autostart removed."
    exit 0
fi

# ------------------------------------------------------------------- python
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install it with:  brew install python3"
    echo "(or get Homebrew first at https://brew.sh)"
    exit 1
fi

# --------------------------------------------------------------- virtualenv
if [ ! -d .venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing/updating dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# ------------------------------------------------- ffmpeg (needed for MP3)
if ! command -v ffmpeg >/dev/null 2>&1; then
    if command -v brew >/dev/null 2>&1; then
        echo "Installing ffmpeg via Homebrew..."
        brew install ffmpeg
    else
        echo "Note: ffmpeg not found and Homebrew not installed."
        echo "Using the bundled fallback binary (imageio-ffmpeg) instead."
    fi
fi

# ------------------------- Rubber Band (optional, better stretch quality)
if command -v rubberband >/dev/null 2>&1; then
    pip install --quiet pyrubberband
    echo "Rubber Band found - using studio-quality time-stretch."
elif command -v brew >/dev/null 2>&1; then
    echo "Tip: 'brew install rubberband' upgrades time-stretch quality."
    echo "     Re-run this script afterwards to enable it."
fi

# ---------------------------------------------------------------- autostart
if [ "$1" = "--install-autostart" ]; then
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.mashupmaker.app</string>
    <key>ProgramArguments</key>
    <array>
        <string>$APP_DIR/.venv/bin/python</string>
        <string>$APP_DIR/app.py</string>
    </array>
    <key>WorkingDirectory</key><string>$APP_DIR</string>
    <key>EnvironmentVariables</key>
    <dict><key>PORT</key><string>$PORT</string></dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>$APP_DIR/mashup.log</string>
    <key>StandardErrorPath</key><string>$APP_DIR/mashup.log</string>
</dict>
</plist>
EOF
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load "$PLIST"
    echo "Autostart installed - Mashup Maker now runs at login (log: mashup.log)."
    echo "It should already be up; give it a few seconds, then open:"
else
    echo
    echo "Starting Mashup Maker..."
fi

# -------------------------------------------------------------- where am I?
HOSTNAME_LOCAL="$(scutil --get LocalHostName 2>/dev/null || hostname -s)"
LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "<this-mac's-IP>")"

echo
echo "=================================================================="
echo "  On this Mac:      http://localhost:$PORT"
echo "  On your phone:    http://$HOSTNAME_LOCAL.local:$PORT"
echo "        (or)        http://$LAN_IP:$PORT"
echo "  (phone must be on the same WiFi network)"
echo "=================================================================="
echo

if [ "$1" = "--install-autostart" ]; then
    exit 0
fi

exec python app.py
