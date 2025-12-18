#!/bin/bash

# Test script for Stage 3: Interactive Session Management
# Tests the new /ask, /session, /start_claude, /stop_claude commands

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Load config
BOT_TOKEN=$(jq -r '.telegram.bot_token' config.json)
CHAT_ID=$(jq -r '.telegram.chat_id' config.json)
SECRET_TOKEN=$(jq -r '.telegram.secret_token' config.json)
WEBHOOK_URL="http://localhost:8000/telegram-webhook"

echo "🧪 Stage 3 Interactive Session Tests"
echo "===================================="
echo ""

# Helper function to send Telegram command
send_command() {
    local cmd="$1"
    echo "📤 Sending: $cmd"

    response=$(curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -H "X-Telegram-Bot-Api-Secret-Token: $SECRET_TOKEN" \
        -d "{
            \"message\": {
                \"chat\": {
                    \"id\": $CHAT_ID
                },
                \"text\": \"$cmd\"
            }
        }")

    if echo "$response" | jq -e '.ok' > /dev/null 2>&1; then
        echo "✅ Command sent successfully"
        return 0
    else
        echo "❌ Failed: $response"
        return 1
    fi
}

# Test 1: Check session status (should be not running initially)
echo "Test 1: Check session status"
echo "----------------------------"
tmux kill-session -t claude 2>/dev/null || true
sleep 1
send_command "/session"
echo ""
sleep 2

# Test 2: Start Claude Code session manually
echo "Test 2: Start Claude Code session"
echo "---------------------------------"
send_command "/start_claude"
echo ""
sleep 5

# Test 3: Check session status again (should be running now)
echo "Test 3: Verify session is running"
echo "---------------------------------"
send_command "/session"
echo ""
sleep 2

# Test 4: Send a simple task
echo "Test 4: Send task via /ask"
echo "-------------------------"
send_command "/ask List files in the current directory"
echo ""
sleep 3

# Test 5: Check status
echo "Test 5: Check tmux status"
echo "------------------------"
send_command "/status"
echo ""
sleep 2

# Test 6: Stop session
echo "Test 6: Stop Claude Code session"
echo "--------------------------------"
send_command "/stop_claude"
echo ""
sleep 2

# Test 7: Auto-start with /ask
echo "Test 7: Auto-start session with /ask"
echo "------------------------------------"
send_command "/ask What is the current date?"
echo ""
sleep 5

# Test 8: Check help
echo "Test 8: Display help"
echo "-------------------"
send_command "/help"
echo ""
sleep 2

echo ""
echo "✅ All tests completed!"
echo ""
echo "📱 Check your Telegram app for the results"
echo ""
echo "Verification checklist:"
echo "  □ /session showed 'not running' initially"
echo "  □ /start_claude started the session"
echo "  □ /session showed 'running' after start"
echo "  □ /ask sent task and showed confirmation"
echo "  □ /status showed tmux output"
echo "  □ /stop_claude stopped the session"
echo "  □ /ask auto-started session and sent task"
echo "  □ /help showed updated command list"
