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
      RESPONSE=$(tail -20 "$TRANSCRIPT" | jq -r 'select(.type == "assistant") | .message.content[0].text // ""' | tail -1 | head -c 400)

      # If empty, try alternative format
      if [ -z "$RESPONSE" ]; then
        RESPONSE=$(tail -20 "$TRANSCRIPT" | jq -r 'select(.role == "assistant") | .content // ""' | tail -1 | head -c 400)
      fi

      # If still empty, show placeholder
      if [ -z "$RESPONSE" ]; then
        RESPONSE="任务已完成，使用 /last_output 查看详情"
      fi
    else
      RESPONSE="无响应内容"
    fi

    # Get timestamp
    TIMESTAMP=$(date '+%H:%M:%S')
    DURATION=$(echo "$INPUT_JSON" | jq -r '.duration_ms // 0')
    DURATION_SEC=$(echo "scale=1; $DURATION / 1000" | bc 2>/dev/null || echo "0")

    MESSAGE="【任务完成】

✓ 时间: ${TIMESTAMP} | 耗时: ${DURATION_SEC}s

响应预览:
───────────────────
${RESPONSE}
───────────────────

※ 使用 /last_output 查看完整响应"
    ;;

  "tool_use")
    # Extract tool execution details
    TOOL=$(echo "$INPUT_JSON" | jq -r '.tool_name // "Unknown"')
    TOOL_INPUT_RAW=$(echo "$INPUT_JSON" | jq -r '.tool_input // {}')
    TOOL_OUTPUT=$(echo "$INPUT_JSON" | jq -r '.tool_output // "无输出"' | head -c 250)

    # Format tool input based on tool type
    case "$TOOL" in
      "Bash")
        TOOL_SYMBOL="◆"
        CMD=$(echo "$TOOL_INPUT_RAW" | jq -r '.command // ""')
        TOOL_INPUT="命令: ${CMD}"
        ;;
      "Read")
        TOOL_SYMBOL="◇"
        FILE=$(echo "$TOOL_INPUT_RAW" | jq -r '.file_path // ""' | sed 's|.*/||')
        TOOL_INPUT="文件: ${FILE}"
        ;;
      "Write")
        TOOL_SYMBOL="▪"
        FILE=$(echo "$TOOL_INPUT_RAW" | jq -r '.file_path // ""' | sed 's|.*/||')
        LINES=$(echo "$TOOL_INPUT_RAW" | jq -r '.content // ""' | wc -l)
        TOOL_INPUT="文件: ${FILE} (${LINES}行)"
        ;;
      "Edit")
        TOOL_SYMBOL="▪"
        FILE=$(echo "$TOOL_INPUT_RAW" | jq -r '.file_path // ""' | sed 's|.*/||')
        TOOL_INPUT="文件: ${FILE}"
        ;;
      "Grep")
        TOOL_SYMBOL="◦"
        PATTERN=$(echo "$TOOL_INPUT_RAW" | jq -r '.pattern // ""')
        TOOL_INPUT="搜索: ${PATTERN}"
        ;;
      "Glob")
        TOOL_SYMBOL="◦"
        PATTERN=$(echo "$TOOL_INPUT_RAW" | jq -r '.pattern // ""')
        TOOL_INPUT="匹配: ${PATTERN}"
        ;;
      *)
        TOOL_SYMBOL="●"
        TOOL_INPUT=$(echo "$TOOL_INPUT_RAW" | jq -c '.' | head -c 150)
        ;;
    esac

    MESSAGE="【工具执行】${TOOL_SYMBOL} ${TOOL}

→ 输入: ${TOOL_INPUT}

输出预览:
${TOOL_OUTPUT}"
    ;;

  "subagent")
    # Extract subagent results
    SUBAGENT=$(echo "$INPUT_JSON" | jq -r '.subagent_type // "Unknown"')
    DESC=$(echo "$INPUT_JSON" | jq -r '.description // "无描述"')
    RESULT=$(echo "$INPUT_JSON" | jq -r '.result // "无结果"' | head -c 350)
    DURATION=$(echo "$INPUT_JSON" | jq -r '.duration_ms // 0')
    DURATION_SEC=$(echo "scale=1; $DURATION / 1000" | bc 2>/dev/null || echo "0")

    # Choose symbol based on subagent type
    case "$SUBAGENT" in
      *explore*|*Explore*)
        AGENT_SYMBOL="◉"
        ;;
      *plan*|*Plan*)
        AGENT_SYMBOL="◆"
        ;;
      *research*|*Research*)
        AGENT_SYMBOL="◇"
        ;;
      *)
        AGENT_SYMBOL="●"
        ;;
    esac

    MESSAGE="【子代理完成】${AGENT_SYMBOL} ${SUBAGENT}

• 任务: ${DESC}
• 耗时: ${DURATION_SEC}s

结果预览:
───────────────────
${RESULT}
───────────────────"
    ;;

  "notification")
    # For generic notifications
    MSG=$(echo "$INPUT_JSON" | jq -r '.message // "通知"')
    MESSAGE="※ 通知: ${MSG}"
    ;;

  *)
    MESSAGE="● 事件: $EVENT_TYPE"
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
import time

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

# Retry configuration
max_retries = 3
retry_delay = 1  # seconds
timeout = 5  # seconds per request

success = False
last_error = None

for attempt in range(1, max_retries + 1):
    try:
        response = requests.post(
            'http://localhost:8000/claude-hook',
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()

        # Success
        print(f'✅ Hook sent successfully (attempt {attempt})', file=sys.stderr)
        success = True
        break

    except requests.exceptions.Timeout as e:
        last_error = f'Timeout after {timeout}s'
        print(f'⏱️  Attempt {attempt}/{max_retries}: {last_error}', file=sys.stderr)

    except requests.exceptions.ConnectionError as e:
        last_error = f'Connection refused (webhook server may not be running)'
        print(f'🔌 Attempt {attempt}/{max_retries}: {last_error}', file=sys.stderr)

    except requests.exceptions.HTTPError as e:
        last_error = f'HTTP {response.status_code}: {response.text[:100]}'
        print(f'❌ Attempt {attempt}/{max_retries}: {last_error}', file=sys.stderr)
        # Don't retry on HTTP errors (4xx, 5xx)
        break

    except Exception as e:
        last_error = str(e)
        print(f'❌ Attempt {attempt}/{max_retries}: {last_error}', file=sys.stderr)

    # Wait before retry (except on last attempt)
    if attempt < max_retries:
        time.sleep(retry_delay)

if not success:
    print(f'⚠️  All {max_retries} attempts failed. Last error: {last_error}', file=sys.stderr)
    print(f'⚠️  Hook notification lost, but not blocking Claude Code execution', file=sys.stderr)

# Always exit 0 to not block Claude Code
sys.exit(0)
" 2>> ~/.claude/hooks.log

# Exit with success
exit 0
