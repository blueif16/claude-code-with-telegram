#!/bin/bash

# This script receives JSON via stdin from Claude Code hooks
# and sends formatted notifications to Telegram

# Auto-detect project root directory (works on macOS and WSL)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to project root to ensure config.json can be found
cd "$PROJECT_ROOT" || exit 1

EVENT_TYPE="$1"  # "stop", "tool_use", "subagent", etc.

# Read JSON from stdin
INPUT_JSON=$(cat)

# Extract key information based on event type
case "$EVENT_TYPE" in
  "stop")
    # Extract transcript path and read the last response
    TRANSCRIPT=$(echo "$INPUT_JSON" | jq -r '.transcript_path // ""')

    if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
      # Read the last assistant message from the transcript
      # Claude Code transcript format: message.content[0].text
      RESPONSE=$(tail -20 "$TRANSCRIPT" | jq -r 'select(.type == "assistant") | .message.content[0].text // ""' | tail -1 | head -c 500)

      # If empty, try alternative format
      if [ -z "$RESPONSE" ]; then
        RESPONSE=$(tail -20 "$TRANSCRIPT" | jq -r 'select(.role == "assistant") | .content // ""' | tail -1 | head -c 500)
      fi

      # If still empty, show placeholder
      if [ -z "$RESPONSE" ]; then
        RESPONSE="Task completed (check /last_output for details)"
      fi
    else
      RESPONSE="No response available"
    fi

    # Get timestamp
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    MESSAGE="✅ Task Completed

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

# Save to local log for /last_output command and debugging
mkdir -p ~/.claude
echo "$INPUT_JSON" > ~/.claude/last_output.json
echo "$(date): EVENT=$EVENT_TYPE" >> ~/.claude/hooks_debug.log
echo "$INPUT_JSON" >> ~/.claude/hooks_debug.log
echo "---" >> ~/.claude/hooks_debug.log

# Send to webhook using Python to properly handle JSON
# Pass JSON via stdin to avoid shell escaping issues
export HOOK_EVENT_TYPE="$EVENT_TYPE"
export HOOK_MESSAGE="$MESSAGE"

echo "$INPUT_JSON" | python3 -c "
import json
import requests
import sys
import os

# Read from environment variables to avoid shell escaping issues
event = os.environ.get('HOOK_EVENT_TYPE', 'unknown')
message = os.environ.get('HOOK_MESSAGE', 'No message')

# Read raw JSON from stdin
raw_json_str = sys.stdin.read().strip()

try:
    raw_data = json.loads(raw_json_str) if raw_json_str else {}
except json.JSONDecodeError as e:
    print(f'JSON parse error: {e}', file=sys.stderr)
    raw_data = {'error': 'Failed to parse JSON', 'raw': raw_json_str[:200]}

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
" 2>> ~/.claude/hooks.log

# Exit with success
exit 0
