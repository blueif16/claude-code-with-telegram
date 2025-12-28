#!/bin/bash

# Test sending message directly to Claude (without / prefix)

CONFIG_FILE="config.json"

# Load config
BOT_TOKEN=$(jq -r '.telegram.bot_token' "$CONFIG_FILE")
CHAT_ID=$(jq -r '.telegram.chat_id' "$CONFIG_FILE")
SECRET_TOKEN=$(jq -r '.telegram.secret_token' "$CONFIG_FILE")

echo "=== Testing Direct Message to Claude ==="
echo ""

# Check if webhook server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Webhook server is not running"
    exit 1
fi

echo "✓ Webhook server is running"

# Check if sub-server is running
if ! curl -s http://localhost:8001/health > /dev/null; then
    echo "❌ Sub-server is not running"
    exit 1
fi

echo "✓ Sub-server is running"
echo ""

# Send a message without / prefix
MESSAGE="测试消息：分析当前目录结构"
echo "Sending message: $MESSAGE"
echo ""

curl -s -X POST http://localhost:8000/telegram-webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $SECRET_TOKEN" \
  -d "{
    \"message\": {
      \"chat\": {\"id\": $CHAT_ID},
      \"text\": \"$MESSAGE\"
    }
  }"

echo ""
echo ""
echo "✓ Message sent"
echo ""
echo "Check your Telegram bot for:"
echo "  - Confirmation that message was sent to Claude"
echo "  - Progress notifications from Claude Code"
echo ""
echo "Check sub-server log:"
echo "  tail -f logs/sub_webhook_claude.log"
