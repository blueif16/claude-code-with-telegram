#!/bin/bash

# Test script for Telegram → Webhook communication

echo "=========================================="
echo "Testing Telegram → Webhook Communication"
echo "=========================================="
echo ""

# Load config
if [ ! -f "config.json" ]; then
  echo "❌ config.json not found!"
  exit 1
fi

CHAT_ID=$(jq -r '.telegram.chat_id' config.json)
SECRET_TOKEN=$(jq -r '.telegram.secret_token' config.json)

if [ "$CHAT_ID" == "YOUR_CHAT_ID_HERE" ]; then
  echo "⚠️  Warning: Please update config.json with your actual CHAT_ID"
  echo "Using placeholder for testing..."
fi

echo "Using CHAT_ID: $CHAT_ID"
echo "Using SECRET_TOKEN: $SECRET_TOKEN"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check..."
RESPONSE=$(curl -s http://localhost:8000/health)
if [ $? -eq 0 ]; then
  echo "✅ Health check passed"
  echo "Response: $RESPONSE"
else
  echo "❌ Health check failed - is webhook_server.py running?"
  exit 1
fi
echo ""

sleep 1

# Test 2: /status command
echo "Test 2: Simulating /status command..."
curl -X POST http://127.0.0.1:8000/telegram-webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $SECRET_TOKEN" \
  -d "{
    \"message\": {
      \"chat\": {
        \"id\": $CHAT_ID
      },
      \"text\": \"/status\"
    }
  }"

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ /status command sent"
else
  echo ""
  echo "❌ /status command failed"
fi
echo ""

sleep 2

# Test 3: /help command
echo "Test 3: Simulating /help command..."
curl -X POST http://127.0.0.1:8000/telegram-webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: $SECRET_TOKEN" \
  -d "{
    \"message\": {
      \"chat\": {
        \"id\": $CHAT_ID
      },
      \"text\": \"/help\"
    }
  }"

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ /help command sent"
else
  echo ""
  echo "❌ /help command failed"
fi
echo ""

sleep 2

# Test 4: Invalid token (should fail)
echo "Test 4: Testing invalid token (should be rejected)..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://127.0.0.1:8000/telegram-webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: invalid-token" \
  -d "{
    \"message\": {
      \"chat\": {
        \"id\": $CHAT_ID
      },
      \"text\": \"/status\"
    }
  }")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" == "403" ]; then
  echo "✅ Invalid token correctly rejected (403)"
else
  echo "❌ Invalid token not rejected properly (got $HTTP_CODE)"
fi
echo ""

echo "=========================================="
echo "Webhook tests completed!"
echo "Check your Telegram to verify responses."
echo "=========================================="
