#!/bin/bash

# Test script for Telegram Bot API connectivity

echo "=========================================="
echo "Testing Telegram Bot API Connectivity"
echo "=========================================="
echo ""

# Load config
if [ ! -f "config.json" ]; then
  echo "❌ config.json not found!"
  exit 1
fi

BOT_TOKEN=$(jq -r '.telegram.bot_token' config.json)
CHAT_ID=$(jq -r '.telegram.chat_id' config.json)

if [ "$BOT_TOKEN" == "YOUR_BOT_TOKEN_HERE" ]; then
  echo "❌ Error: Please update config.json with your actual BOT_TOKEN"
  exit 1
fi

if [ "$CHAT_ID" == "YOUR_CHAT_ID_HERE" ]; then
  echo "❌ Error: Please update config.json with your actual CHAT_ID"
  exit 1
fi

echo "Using BOT_TOKEN: ${BOT_TOKEN:0:10}..."
echo "Using CHAT_ID: $CHAT_ID"
echo ""

# Test 1: Get Bot Info
echo "Test 1: Getting bot information..."
RESPONSE=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
SUCCESS=$(echo "$RESPONSE" | jq -r '.ok')

if [ "$SUCCESS" == "true" ]; then
  BOT_NAME=$(echo "$RESPONSE" | jq -r '.result.username')
  echo "✅ Bot connected successfully: @$BOT_NAME"
else
  echo "❌ Failed to connect to bot"
  echo "Response: $RESPONSE"
  exit 1
fi
echo ""

sleep 1

# Test 2: Send Test Message
echo "Test 2: Sending test message to Telegram..."
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=$CHAT_ID" \
  -d "text=Test message from test_telegram.sh")

SUCCESS=$(echo "$RESPONSE" | jq -r '.ok')

if [ "$SUCCESS" == "true" ]; then
  MESSAGE_ID=$(echo "$RESPONSE" | jq -r '.result.message_id')
  echo "✅ Test message sent successfully (message_id: $MESSAGE_ID)"
else
  echo "❌ Failed to send test message"
  echo "Response: $RESPONSE"
  exit 1
fi
echo ""

sleep 1

# Test 3: Get Updates
echo "Test 3: Getting recent updates..."
RESPONSE=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?limit=5")
SUCCESS=$(echo "$RESPONSE" | jq -r '.ok')

if [ "$SUCCESS" == "true" ]; then
  UPDATE_COUNT=$(echo "$RESPONSE" | jq '.result | length')
  echo "✅ Retrieved $UPDATE_COUNT recent updates"

  if [ "$UPDATE_COUNT" -gt 0 ]; then
    echo ""
    echo "Recent messages:"
    echo "$RESPONSE" | jq -r '.result[] | "  - [\(.message.date | strftime("%Y-%m-%d %H:%M:%S"))] \(.message.text // "No text")"' | head -5
  fi
else
  echo "❌ Failed to get updates"
  echo "Response: $RESPONSE"
fi
echo ""

echo "=========================================="
echo "Telegram API tests completed!"
echo "Check your Telegram app to verify the test message."
echo "=========================================="
