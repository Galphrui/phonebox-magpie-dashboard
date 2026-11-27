#!/bin/bash
set -euo pipefail

LABEL="com.galph.phonebox-magpie"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
if [[ -f "$PLIST" ]]; then
  rm "$PLIST"
fi
echo "Removed the magpie bridge launch agent. PhoneBox pages and bridge files were kept."
