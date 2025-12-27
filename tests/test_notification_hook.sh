#!/bin/bash

# 测试 Notification hook 是否能捕获 AskUserQuestion 的 idle_prompt 事件

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== 测试 Notification Hook 捕获 AskUserQuestion ==="
echo ""

# 创建模拟的 transcript 文件
TEMP_TRANSCRIPT=$(mktemp)
cat > "$TEMP_TRANSCRIPT" << 'EOF'
{"type":"assistant","message":{"content":[{"type":"tool_use","name":"AskUserQuestion","input":{"questions":[{"question":"选择认证方式？","header":"认证","options":[{"label":"JWT","description":"使用 JWT token"},{"label":"Session","description":"使用 session cookie"}],"multiSelect":false}]}}]}}
EOF

# 构造 idle_prompt 事件的 JSON
TEST_JSON=$(cat <<EOF
{
  "notification_type": "idle_prompt",
  "message": "Claude 正在等待你的回答",
  "transcript_path": "$TEMP_TRANSCRIPT"
}
EOF
)

echo "📝 测试数据:"
echo "$TEST_JSON" | jq '.'
echo ""

echo "🔧 执行 hook 脚本..."
echo "$TEST_JSON" | "$PROJECT_ROOT/.claude/notify-telegram-smart.sh" notification

echo ""
echo "📋 检查日志输出:"
tail -5 ~/.claude/hooks_debug.log

echo ""
echo "✅ 测试完成"
echo ""
echo "预期结果:"
echo "  - hook 脚本应该识别 idle_prompt 事件"
echo "  - 应该从 transcript 提取 questions 数据"
echo "  - 应该设置 IS_QUESTION=true"
echo "  - 应该发送到 webhook 服务器"

# 清理
rm -f "$TEMP_TRANSCRIPT"
