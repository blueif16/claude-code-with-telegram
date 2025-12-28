#!/bin/bash

# Test session switching via callback button
# This script simulates clicking a button to switch tmux session

CONFIG_FILE="config.json"

# Load config
BOT_TOKEN=$(jq -r '.telegram.bot_token' "$CONFIG_FILE")
CHAT_ID=$(jq -r '.telegram.chat_id' "$CONFIG_FILE")
SECRET_TOKEN=$(jq -r '.telegram.secret_token' "$CONFIG_FILE")

echo "=== Testing Session Switch Callback ==="
echo ""

# Check if webhook server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Webhook server is not running"
    exit 1
fi

echo "✓ Webhook server is running"
echo ""

# Get current tmux session from config
CURRENT_SESSION=$(jq -r '.claude.tmux_session' "$CONFIG_FILE")
echo "Current session in config: $CURRENT_SESSION"
echo ""

# List available sessions
echo "Available tmux sessions:"
tmux list-sessions -F "#{session_name}" 2>/dev/null || echo "No sessions"
echo ""

# Choose a different session to switch to
TARGET_SESSION="p0-smart-filter"
echo "Testing switch to: $TARGET_SESSION"
echo ""

# Simulate callback query (button click)
echo "Sending callback query to webhook..."
curl -s -X POST http://localhost:8000/telegram-webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $SECRET_TOKEN" \
  -d "{
    \"callback_query\": {
      \"id\": \"test_callback_$(date +%s)\",
      \"from\": {\"id\": $CHAT_ID},
      \"data\": \"switch_session_$TARGET_SESSION\"
    }
  }"

echo ""
echo ""

# Check updated config
NEW_SESSION=$(jq -r '.claude.tmux_session' "$CONFIG_FILE")
echo "Session after switch: $NEW_SESSION"
echo ""

if [ "$NEW_SESSION" = "$TARGET_SESSION" ]; then
    echo "✓ Session switched successfully!"
else
    echo "⚠ Session may not have changed (check if it's a project-specific session)"
fi

echo ""
echo "Check your Telegram bot for:"
echo "  - Popup notification confirming the switch"
echo "  - Message with instructions for the new session"
