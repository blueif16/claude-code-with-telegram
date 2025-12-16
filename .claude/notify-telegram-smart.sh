#!/bin/bash

# This script receives JSON via stdin from Claude Code hooks
# and sends formatted notifications to Telegram

EVENT_TYPE="$1"  # "stop", "tool_use", "subagent", etc.

# Read JSON from stdin
INPUT_JSON=$(cat)

# Extract key information based on event type
case "$EVENT_TYPE" in
  "stop")
    # Extract Claude's response and metadata
    RESPONSE=$(echo "$INPUT_JSON" | jq -r '.response // "No response"' | head -c 500)
    DURATION=$(echo "$INPUT_JSON" | jq -r '.duration_ms // 0')
    TIMESTAMP=$(echo "$INPUT_JSON" | jq -r '.timestamp // "Unknown"')

    MESSAGE="Task Completed

Duration: ${DURATION}ms
Time: ${TIMESTAMP}

Response Preview:
${RESPONSE}

Use /last_output for full response"
    ;;

  "tool_use")
    # Extract tool execution details
    TOOL=$(echo "$INPUT_JSON" | jq -r '.tool_name // "Unknown"')
    TOOL_INPUT=$(echo "$INPUT_JSON" | jq -r '.tool_input | tostring' | head -c 200)
    TOOL_OUTPUT=$(echo "$INPUT_JSON" | jq -r '.tool_output // "No output"' | head -c 300)

    MESSAGE="Tool Executed

Tool: $TOOL

Input:
${TOOL_INPUT}

Output Preview:
${TOOL_OUTPUT}"
    ;;

  "subagent")
    # Extract subagent results
    SUBAGENT=$(echo "$INPUT_JSON" | jq -r '.subagent_type // "Unknown"')
    DESC=$(echo "$INPUT_JSON" | jq -r '.description // "No description"')
    RESULT=$(echo "$INPUT_JSON" | jq -r '.result // "No result"' | head -c 400)
    DURATION=$(echo "$INPUT_JSON" | jq -r '.duration_ms // 0')

    MESSAGE="Subagent Completed

Type: $SUBAGENT
Task: $DESC
Duration: ${DURATION}ms

Result Preview:
${RESULT}"
    ;;

  "notification")
    # For generic notifications
    MSG=$(echo "$INPUT_JSON" | jq -r '.message // "Notification"')
    MESSAGE="Notification: ${MSG}"
    ;;

  *)
    MESSAGE="Event: $EVENT_TYPE"
    ;;
esac

# Save to local log for /last_output command
mkdir -p ~/.claude
echo "$INPUT_JSON" > ~/.claude/last_output.json

# Send to webhook using Python to properly handle JSON
python3 -c "
import json
import requests
import sys

event = sys.argv[1]
message = sys.argv[2]
raw_data = json.loads(sys.argv[3])

payload = {
    'event': event,
    'message': message,
    'raw_data': raw_data
}

try:
    response = requests.post(
        'http://localhost:8000/claude-hook',
        json=payload,
        timeout=5
    )
    response.raise_for_status()
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" "$EVENT_TYPE" "$MESSAGE" "$INPUT_JSON" 2>> ~/.claude/hooks.log

# Exit with success
exit 0
