#!/bin/bash

# Test script for Claude Hook → Telegram notification

echo "=========================================="
echo "Testing Claude Hook → Telegram Notification"
echo "=========================================="
echo ""

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Test 1: Stop Hook
echo "Test 1: Simulating Stop Hook..."
echo '{
  "response": "Test task completed successfully",
  "duration_ms": 1234,
  "timestamp": "2025-12-14T10:30:00Z"
}' | "$PROJECT_ROOT/.claude/notify-telegram-smart.sh" stop

if [ $? -eq 0 ]; then
  echo "✅ Stop hook test sent"
else
  echo "❌ Stop hook test failed"
fi
echo ""

sleep 2

# Test 2: Tool Use Hook
echo "Test 2: Simulating Tool Use Hook..."
echo '{
  "tool_name": "Bash",
  "tool_input": {
    "command": "ls -la",
    "description": "List files"
  },
  "tool_output": "total 48\ndrwxr-xr-x  12 user  staff  384 Dec 14 10:30 .",
  "timestamp": "2025-12-14T10:30:00Z"
}' | "$PROJECT_ROOT/.claude/notify-telegram-smart.sh" tool_use

if [ $? -eq 0 ]; then
  echo "✅ Tool use hook test sent"
else
  echo "❌ Tool use hook test failed"
fi
echo ""

sleep 2

# Test 3: Subagent Hook
echo "Test 3: Simulating Subagent Hook..."
echo '{
  "subagent_type": "explore",
  "description": "Search for error handling",
  "result": "Found 3 files with error handling patterns",
  "duration_ms": 5678,
  "timestamp": "2025-12-14T10:30:00Z"
}' | "$PROJECT_ROOT/.claude/notify-telegram-smart.sh" subagent

if [ $? -eq 0 ]; then
  echo "✅ Subagent hook test sent"
else
  echo "❌ Subagent hook test failed"
fi
echo ""

echo "=========================================="
echo "Hook tests completed!"
echo "Check your Telegram to verify messages were received."
echo "=========================================="
