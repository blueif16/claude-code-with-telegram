#!/bin/bash

# 模拟 Notification hook 发送 idle_prompt 事件
# 这个脚本用于测试 notify-telegram-smart.sh 的 notification 处理逻辑

# 创建一个模拟的 transcript 文件
MOCK_TRANSCRIPT="/tmp/mock_transcript_$$.jsonl"

# 写入模拟的 AskUserQuestion 工具调用
cat > "$MOCK_TRANSCRIPT" <<'EOF'
{"type":"assistant","message":{"content":[{"type":"tool_use","name":"AskUserQuestion","input":{"questions":[{"header":"测试","question":"这是一个测试问题？","options":[{"label":"选项A","description":"第一个选项"},{"label":"选项B","description":"第二个选项"}],"multiSelect":false}]}}]}}
EOF

# 构造 Notification hook 的 JSON 输入
NOTIFICATION_JSON=$(cat <<EOF
{
  "notification_type": "idle_prompt",
  "message": "Waiting for user input...",
  "transcript_path": "$MOCK_TRANSCRIPT"
}
EOF
)

echo "测试 Notification hook 的 idle_prompt 处理..."
echo "$NOTIFICATION_JSON" | /Users/tk/Desktop/claude-code-with-telegram/.claude/notify-telegram-smart.sh notification

# 清理
rm -f "$MOCK_TRANSCRIPT"

echo ""
echo "检查 webhook 日志中是否收到 is_question=true 的事件..."
tail -5 /Users/tk/Desktop/claude-code-with-telegram/logs/webhook.log | grep "is_question"
