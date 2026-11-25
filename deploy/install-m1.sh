#!/bin/zsh
# Sets World Watch up on the home Mac (the M1) as a background service: it starts when the Mac logs in,
# restarts itself if it ever stops, and survives reboots. Same pattern as the music server.
#
#   cd ~/WorldWatch && ./deploy/install-m1.sh
#
# Collected data, keys and logs live in ~/worldwatch-data (outside the code folder, so a new copy of the
# code never touches them). Put key files there (aisstream-key.txt, opensanctions-key.txt, ...).
# The map is served on all interfaces, port 8710: open it from another device at http://<M1's Tailscale IP>:8710/.
# Don't open it in Safari on the M1 itself: the globe is the heavy part and belongs on the viewing device.
set -eu

ROOT=${0:A:h:h}
SERVER=$ROOT/server
DATA=$HOME/worldwatch-data
LABEL=local.worldwatch.server
PLIST=$HOME/Library/LaunchAgents/$LABEL.plist
PORT=8710
export PATH=/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin

command -v uv >/dev/null || { echo "Missing: uv. Install it with: brew install uv"; exit 1; }
UV=$(command -v uv)
mkdir -p "$DATA/logs"
(cd "$SERVER" && "$UV" sync --frozen --quiet)

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>$UV</string><string>run</string><string>--frozen</string><string>python</string><string>-m</string><string>worldwatch</string><string>serve</string>
  </array>
  <key>WorkingDirectory</key><string>$SERVER</string>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>$PATH</string>
    <key>WW_DATA</key><string>$DATA</string>
    <key>WW_HOST</key><string>0.0.0.0</string>
    <key>WW_PORT</key><string>$PORT</string>
    <key>WW_LOOKUP_REMOTE</key><string>1</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>$DATA/logs/server.out</string>
  <key>StandardErrorPath</key><string>$DATA/logs/server.out</string>
</dict></plist>
PLIST

launchctl bootout gui/$(id -u)/$LABEL 2>/dev/null || true
launchctl bootstrap gui/$(id -u) "$PLIST"
for i in {1..60}; do curl -s -o /dev/null localhost:$PORT/ && break; sleep 1; done
curl -s -o /dev/null localhost:$PORT/ && echo "World Watch is running on port $PORT" || { echo "It didn't start; see $DATA/logs/server.out"; exit 1; }
