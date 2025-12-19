#!/bin/bash

# Local-only webhook test - no Telegram API calls
# This tests the webhook server and Claude Code hook integration locally

echo "=========================================="
echo "🧪 LOCAL WEBHOOK TEST (No Telegram)"
echo "=========================================="
echo ""

# Check if webhook server is running
echo "Step 1: Checking if webhook server is running..."
HEALTH_CHECK=$(curl -s http://localhost:8000/health 2>/dev/null)

if [ $? -ne 0 ]; then
  echo "❌ Webhook server is not running!"
  echo ""
  echo "Please start it in TEST_MODE:"
  echo "  TEST_MODE=1 python3 webhook_server.py"
  echo ""
  exit 1
fi

echo "✅ Webhook server is running"
echo "Response: $HEALTH_CHECK"
echo ""

sleep 1

# Test 1: Direct POST to /claude-hook endpoint
echo "=========================================="
echo "Test 1: Simulating Stop Hook"
echo "=========================================="

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "stop",
    "message": "Test stop event",
    "raw_data": {
      "response": "This is a test Claude response",
      "duration_ms": 1234,
      "timestamp": "2025-12-14T10:30:00Z"
    }
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
  echo "✅ Stop hook received successfully"
  echo "Response: $BODY"
else
  echo "❌ Stop hook failed (HTTP $HTTP_CODE)"
  echo "Response: $BODY"
fi
echo ""

sleep 2

# Test 2: Tool Use Hook
echo "=========================================="
echo "Test 2: Simulating Tool Use Hook"
echo "=========================================="

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "tool_use",
    "message": "Test tool execution",
    "raw_data": {
      "tool_name": "Bash",
      "tool_input": {
        "command": "ls -la",
        "description": "List files"
      },
      "tool_output": "total 48\ndrwxr-xr-x  12 user  staff  384 Dec 14 10:30 .",
      "timestamp": "2025-12-14T10:30:00Z"
    }
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
  echo "✅ Tool use hook received successfully"
  echo "Response: $BODY"
else
  echo "❌ Tool use hook failed (HTTP $HTTP_CODE)"
  echo "Response: $BODY"
fi
echo ""

sleep 2

# Test 3: Subagent Hook
echo "=========================================="
echo "Test 3: Simulating Subagent Hook"
echo "=========================================="

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "subagent",
    "message": "Test subagent completion",
    "raw_data": {
      "subagent_type": "explore",
      "description": "Search for error handling",
      "result": "Found 3 files with error handling patterns",
      "duration_ms": 5678,
      "timestamp": "2025-12-14T10:30:00Z"
    }
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "200" ]; then
  echo "✅ Subagent hook received successfully"
  echo "Response: $BODY"
else
  echo "❌ Subagent hook failed (HTTP $HTTP_CODE)"
  echo "Response: $BODY"
fi
echo ""

sleep 2

# Test 4: Test the notify script directly
echo "=========================================="
echo "Test 4: Testing notify-telegram-smart.sh"
echo "=========================================="

if [ -f ".claude/notify-telegram-smart.sh" ]; then
  echo "Sending test data through notify script..."
  echo '{
    "response": "Direct script test",
    "duration_ms": 999,
    "timestamp": "2025-12-14T10:30:00Z"
  }' | ./.claude/notify-telegram-smart.sh stop

  if [ $? -eq 0 ]; then
    echo "✅ Notify script executed successfully"
  else
    echo "❌ Notify script failed"
  fi
else
  echo "⚠️  notify-telegram-smart.sh not found at .claude/notify-telegram-smart.sh"
fi
echo ""

sleep 2

# Test 5: Check stored data
echo "=========================================="
echo "Test 5: Verifying Data Storage"
echo "=========================================="

HEALTH_CHECK=$(curl -s http://localhost:8000/health)
echo "Current storage state:"
echo "$HEALTH_CHECK" | jq '.'
echo ""

# Check logs
echo "=========================================="
echo "Recent Webhook Logs:"
echo "=========================================="
if [ -f "logs/webhook.log" ]; then
  tail -n 10 logs/webhook.log
else
  echo "⚠️  No webhook.log found"
fi
echo ""

echo "=========================================="
echo "✅ Local webhook tests completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Check the webhook server console output"
echo "2. Verify all messages were logged correctly"
echo "3. Review logs/webhook.log for details"
echo ""
echo "To test with Claude Code hooks:"
echo "1. Copy .claude/settings.json to ~/.claude/settings.json"
echo "2. Restart Claude Code"
echo "3. Execute any task in Claude Code"
echo "4. Check webhook logs for incoming hook data"
