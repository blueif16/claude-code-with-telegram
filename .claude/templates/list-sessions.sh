#!/bin/bash
# list-sessions.sh - 列出最近使用的项目 sessions
# 返回: JSON 格式的 sessions 列表

set -e

HISTORY_FILE="$HOME/.claude-telegram/sessions.json"

# 检查历史文件是否存在
if [ ! -f "$HISTORY_FILE" ]; then
    cat <<'EOF'
{
  "sessions": []
}
EOF
    exit 0
fi

# 读取并返回 sessions
cat "$HISTORY_FILE"
