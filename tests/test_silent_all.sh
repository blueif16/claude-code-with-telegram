#!/bin/bash

echo "=========================================="
echo "🧪 测试完全静默模式（只接收Stop事件）"
echo "=========================================="
echo ""

# 测试1: Stop事件（应该发送）
echo "测试1: Stop事件（应该发送）"
curl -s -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "stop",
    "message": "【任务完成】测试消息",
    "raw_data": {"duration_ms": 1000}
  }'
echo " ✓"
sleep 1

# 测试2: Subagent（应该静默）
echo "测试2: Subagent事件（应该静默）"
curl -s -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "subagent",
    "message": "【子代理完成】Explore",
    "raw_data": {"subagent_type": "Explore"}
  }'
echo " ✓"
sleep 1

# 测试3: Tool Use（应该静默）
echo "测试3: Tool Use事件（应该静默）"
curl -s -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "tool_use",
    "message": "【工具执行】Read",
    "raw_data": {"tool_name": "Read"}
  }'
echo " ✓"
sleep 1

echo ""
echo "=========================================="
echo "📊 测试完成"
echo "=========================================="
echo ""
echo "预期结果："
echo "  ✓ Stop事件 - 应该收到Telegram通知"
echo "  ✗ Subagent - 不应收到通知（被静默）"
echo "  ✗ Tool Use - 不应收到通知（被静默）"
echo ""
echo "查看日志确认："
tail -20 logs/webhook.log | grep -E "(Silencing|Notification)"
echo ""
