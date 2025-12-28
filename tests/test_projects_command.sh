#!/bin/bash

# Test /projects command
# This script tests the /projects command which lists tmux sessions

CONFIG_FILE="config.json"

# Load config
BOT_TOKEN=$(jq -r '.telegram.bot_token' "$CONFIG_FILE")
CHAT_ID=$(jq -r '.telegram.chat_id' "$CONFIG_FILE")
SECRET_TOKEN=$(jq -r '.telegram.secret_token' "$CONFIG_FILE")

echo "=== Testing /projects Command ==="
echo ""

# Check if webhook server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Webhook server is not running"
    echo "Please start it with: python3 webhook_server.py"
    exit 1
fi

echo "✓ Webhook server is running"
echo ""

# List current tmux sessions
echo "Current tmux sessions:"
tmux list-sessions 2>/dev/null || echo "No tmux sessions running"
echo ""

# Send /projects command via Telegram webhook
echo "Sending /projects command to webhook..."
curl -s -X POST http://localhost:8000/telegram-webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $SECRET_TOKEN" \
  -d "{
    \"message\": {
      \"chat\": {\"id\": $CHAT_ID},
      \"text\": \"/projects\"
    }
  }"

echo ""
echo ""
echo "✓ Command sent"
echo ""
echo "Check your Telegram bot for the response with inline keyboard buttons"
echo "You should see:"
echo "  - List of all running tmux sessions"
echo "  - Session info (windows, attached status)"
echo "  - Inline keyboard buttons to switch sessions"
