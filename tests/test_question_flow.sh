#!/bin/bash

# Test AskUserQuestion end-to-end flow
# This simulates Claude Code sending an AskUserQuestion notification

echo "🧪 Testing AskUserQuestion Flow"
echo "================================"

# Create a mock transcript with AskUserQuestion (JSONL format - one JSON per line)
MOCK_TRANSCRIPT=$(mktemp)
cat > "$MOCK_TRANSCRIPT" << 'EOF'
{"type":"user","message":"test"}
{"type":"assistant","message":{"content":[{"type":"tool_use","name":"AskUserQuestion","input":{"questions":[{"question":"Which authentication method should we use?","header":"Auth method","multiSelect":false,"options":[{"label":"JWT","description":"JSON Web Tokens for stateless auth"},{"label":"Session","description":"Server-side session management"}]}]}}]}}
EOF

echo "✓ Created mock transcript: $MOCK_TRANSCRIPT"

# Create mock notification JSON
MOCK_JSON=$(cat << EOF
{
  "notification_type": "idle_prompt",
  "message": "Claude 需要你的回答",
  "transcript_path": "$MOCK_TRANSCRIPT"
}
EOF
)

echo "✓ Created mock notification JSON"
echo ""
echo "📤 Sending to hook script..."
echo ""

# Send to hook script
echo "$MOCK_JSON" | ./.claude/notify-telegram-smart.sh notification

echo ""
echo "================================"
echo "✓ Test completed"
echo ""
echo "Check:"
echo "1. Telegram bot should have received a message with inline buttons"
echo "2. Check logs: tail -20 logs/webhook.log"
echo "3. Check hook logs: tail -20 ~/.claude/hooks.log"

# Keep transcript for inspection
echo ""
echo "Mock transcript kept at: $MOCK_TRANSCRIPT"
echo "Run 'rm $MOCK_TRANSCRIPT' to clean up manually"
