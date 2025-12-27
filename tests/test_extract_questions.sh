#!/bin/bash

TRANSCRIPT="/var/folders/bm/_d43rmvj30q64mm29lx109mw0000gn/T/tmp.OVVfUWfq1n"

echo "=== Testing question extraction ==="
echo ""
echo "1. Transcript content:"
cat "$TRANSCRIPT"
echo ""
echo ""
echo "2. Extracting questions with jq:"
QUESTIONS=$(tail -50 "$TRANSCRIPT" | jq -c 'select(.type == "assistant") | .message.content[] | select(.name == "AskUserQuestion") | .input.questions' 2>/dev/null | tail -1)
echo "Result: $QUESTIONS"
echo ""
echo "3. Check if empty:"
if [ -n "$QUESTIONS" ] && [ "$QUESTIONS" != "null" ] && [ "$QUESTIONS" != "" ]; then
    echo "✓ Questions extracted successfully!"
    echo "Questions data: $QUESTIONS"
else
    echo "✗ Failed to extract questions"
    echo "QUESTIONS variable: '$QUESTIONS'"
fi
