#!/bin/bash

# Test PreToolUse hook for AskUserQuestion
# This simulates Claude Code calling PreToolUse hook before AskUserQuestion

echo "🧪 Testing PreToolUse Hook for AskUserQuestion"
echo "=============================================="

# Create mock PreToolUse JSON (format that Claude Code sends to PreToolUse hook)
MOCK_JSON=$(cat << 'EOF'
{
  "tool_name": "AskUserQuestion",
  "tool_input": {
    "questions": [
      {
        "question": "Which authentication method should we use?",
        "header": "Auth method",
        "multiSelect": false,
        "options": [
          {
            "label": "JWT",
            "description": "JSON Web Tokens for stateless auth"
          },
          {
            "label": "Session",
            "description": "Server-side session management"
          }
        ]
      }
    ]
  }
}
EOF
)

echo "✓ Created mock PreToolUse JSON"
echo ""
echo "📤 Sending to hook script (ask_question event)..."
echo ""

# Send to hook script
echo "$MOCK_JSON" | ./.claude/notify-telegram-smart.sh ask_question

echo ""
echo "=============================================="
echo "✓ Test completed"
echo ""
echo "Check:"
echo "1. Telegram bot should have received a message with inline buttons"
echo "2. Check logs: tail -20 logs/webhook.log"
echo "3. Check hook logs: tail -20 ~/.claude/hooks.log"
echo "4. Check debug log: tail -20 ~/.claude/hooks_debug.log"
