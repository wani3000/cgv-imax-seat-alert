#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
RUNTIME_DIR="$HOME/Library/Application Support/cgv-imax-seat-alert"
AGENT_FILE="$HOME/Library/LaunchAgents/com.wani3000.cgv-imax-subscription.plist"
USER_ID=$(id -u)

if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "Missing .env. Copy .env.example to .env and add the Telegram token first." >&2
  exit 1
fi

mkdir -p "$RUNTIME_DIR/data" "$HOME/Library/LaunchAgents"
install -m 700 "$PROJECT_DIR/subscription_bot.py" "$PROJECT_DIR/monitor_core.py" "$PROJECT_DIR/payment_identity.py" "$RUNTIME_DIR/"
install -m 600 "$PROJECT_DIR/.env" "$RUNTIME_DIR/.env"
if [ -f "$PROJECT_DIR/data/subscribers.json" ]; then
  install -m 600 "$PROJECT_DIR/data/subscribers.json" "$RUNTIME_DIR/data/subscribers.json"
fi

sed \
  -e "s|__PYTHON__|/usr/bin/python3|g" \
  -e "s|__RUNTIME__|$RUNTIME_DIR|g" \
  "$PROJECT_DIR/macos/com.wani3000.cgv-imax-subscription.plist.template" > "$AGENT_FILE"
plutil -lint "$AGENT_FILE"
launchctl bootout "gui/$USER_ID/com.wani3000.cgv-imax-subscription" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$USER_ID" "$AGENT_FILE"
launchctl print "gui/$USER_ID/com.wani3000.cgv-imax-subscription" | grep -E 'state =|pid ='
