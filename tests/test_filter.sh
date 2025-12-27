#!/bin/bash

echo "=========================================="
echo "🧪 测试智能通知过滤功能"
echo "=========================================="
echo ""

# 测试1: Stop事件（应该发送）
echo "测试1: Stop事件（重要事件，应该发送）"
curl -s -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "stop",
    "message": "【任务完成】测试消息",
    "raw_data": {"duration_ms": 1000}
  }'
echo ""
echo "✓ Stop事件已发送"
echo ""

sleep 1

# 测试2: Tool Use - Read（应该静默）
echo "测试2: Tool Use - Read（静默工具，不应发送）"
curl -s -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "tool_use",
    "message": "【工具执行】Read",
    "raw_data": {"tool_name": "Read", "tool_input": {"file_path": "test.txt"}}
  }'
echo ""
echo "✓ Read工具事件已发送（应该被静默）"
echo ""

sleep 1

# 测试3: Tool Use - Bash（应该静默）
echo "测试3: Tool Use - Bash（静默工具，不应发送）"
curl -s -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "tool_use",
    "message": "【工具执行】Bash",
    "raw_data": {"tool_name": "Bash", "tool_input": {"command": "ls"}}
  }'
echo ""
echo "✓ Bash工具事件已发送（应该被静默）"
echo ""

sleep 1

# 测试4: Subagent（应该发送）
echo "测试4: Subagent事件（重要事件，应该发送）"
curl -s -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "subagent",
    "message": "【子代理完成】Explore",
    "raw_data": {"subagent_type": "Explore", "description": "探索代码库"}
  }'
echo ""
echo "✓ Subagent事件已发送"
echo ""

sleep 1

# 测试5: Tool Use - 非静默工具（应该发送）
echo "测试5: Tool Use - WebFetch（非静默工具，应该发送）"
curl -s -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "tool_use",
    "message": "【工具执行】WebFetch",
    "raw_data": {"tool_name": "WebFetch", "tool_input": {"url": "https://example.com"}}
  }'
echo ""
echo "✓ WebFetch工具事件已发送"
echo ""

echo "=========================================="
echo "📊 测试完成"
echo "=========================================="
echo ""
echo "预期结果："
echo "  ✓ Stop事件 - 应该收到Telegram通知"
echo "  ✗ Read工具 - 不应收到通知（被静默）"
echo "  ✗ Bash工具 - 不应收到通知（被静默）"
echo "  ✓ Subagent - 应该收到Telegram通知"
echo "  ✓ WebFetch - 应该收到Telegram通知"
echo ""
echo "请检查："
echo "  1. Telegram中应该只收到3条消息（Stop、Subagent、WebFetch）"
echo "  2. 查看日志: tail -f logs/webhook.log"
echo ""
