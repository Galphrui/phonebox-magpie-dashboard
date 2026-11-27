#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP_SUPPORT="$HOME/Library/Application Support/PhoneBox"
BRIDGE_DIR="$APP_SUPPORT/bridge"
PLIST="$HOME/Library/LaunchAgents/com.galph.phonebox-magpie.plist"
LABEL="com.galph.phonebox-magpie"
LOG="$HOME/Library/Logs/phonebox-magpie.log"

[[ "$(uname -s)" == "Darwin" ]] || { echo "This installer supports macOS." >&2; exit 1; }
command -v python3 >/dev/null || { echo "Install Python 3 and retry." >&2; exit 1; }

mkdir -p "$BRIDGE_DIR" "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
install -m 755 "$ROOT/bridge/magpie-bridge.py" "$BRIDGE_DIR/magpie-bridge.py"
python3 "$ROOT/scripts/apply-dashboard.py"

PHONEBOX_BRIDGE_PATH="$BRIDGE_DIR/magpie-bridge.py" PHONEBOX_LOG_PATH="$LOG" PHONEBOX_LABEL="$LABEL" \
  python3 - "$PLIST" <<'PY'
import os
import plistlib
import sys

document = {
    "Label": os.environ["PHONEBOX_LABEL"],
    "ProgramArguments": ["/usr/bin/python3", os.environ["PHONEBOX_BRIDGE_PATH"]],
    "RunAtLoad": True,
    "StartInterval": 2,
    "StandardOutPath": os.environ["PHONEBOX_LOG_PATH"],
    "StandardErrorPath": os.environ["PHONEBOX_LOG_PATH"],
}
with open(sys.argv[1], "wb") as stream:
    plistlib.dump(document, stream)
PY

DOMAIN="gui/$(id -u)"
launchctl bootout "$DOMAIN" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl kickstart -k "$DOMAIN/$LABEL"
echo "Installed. The magpie bridge refreshes every 2 seconds."
