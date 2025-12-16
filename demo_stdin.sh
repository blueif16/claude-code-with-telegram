#!/bin/bash

# stdin 机制演示脚本
# 这个脚本演示了 Claude Code hooks 如何通过 stdin 传递数据

echo "=========================================="
echo "stdin 机制演示"
echo "=========================================="
echo ""

# 演示 1: 基本的 stdin 读取
echo "演示 1: 基本的 stdin 读取"
echo "----------------------------------------"
echo "命令: echo 'Hello World' | cat"
echo "结果:"
echo "Hello World" | cat
echo ""

# 演示 2: 在脚本中读取 stdin
echo "演示 2: 创建临时脚本读取 stdin"
echo "----------------------------------------"
cat > /tmp/demo_read.sh << 'EOF'
#!/bin/bash
DATA=$(cat)
echo "脚本接收到: $DATA"
EOF
chmod +x /tmp/demo_read.sh

echo "命令: echo 'Test Data' | /tmp/demo_read.sh"
echo "结果:"
echo "Test Data" | /tmp/demo_read.sh
echo ""

# 演示 3: 读取 JSON 数据
echo "演示 3: 读取和解析 JSON 数据"
echo "----------------------------------------"
cat > /tmp/demo_json.sh << 'EOF'
#!/bin/bash
JSON_DATA=$(cat)
echo "原始 JSON:"
echo "$JSON_DATA"
echo ""
echo "解析后的字段:"
echo "  name: $(echo "$JSON_DATA" | jq -r '.name')"
echo "  age: $(echo "$JSON_DATA" | jq -r '.age')"
echo "  city: $(echo "$JSON_DATA" | jq -r '.city')"
EOF
chmod +x /tmp/demo_json.sh

echo "命令: echo '{\"name\":\"Alice\",\"age\":30,\"city\":\"Beijing\"}' | /tmp/demo_json.sh"
echo "结果:"
echo '{"name":"Alice","age":30,"city":"Beijing"}' | /tmp/demo_json.sh
echo ""

# 演示 4: 模拟 Claude Code 的 Stop Hook
echo "演示 4: 模拟 Claude Code 的 Stop Hook"
echo "----------------------------------------"
echo "这就是 Claude Code 实际做的事情："
echo ""
echo "Claude Code 内部执行（伪代码）："
echo "  json = {\"response\":\"Task completed\",\"duration_ms\":1234}"
echo "  execute_with_stdin(\"notify-telegram-smart.sh stop\", json)"
echo ""
echo "等价于命令行："
echo "  echo '{...}' | notify-telegram-smart.sh stop"
echo ""
echo "实际执行:"

cat > /tmp/demo_hook.sh << 'EOF'
#!/bin/bash
EVENT_TYPE="$1"
INPUT_JSON=$(cat)

echo "事件类型: $EVENT_TYPE"
echo "接收到的 JSON:"
echo "$INPUT_JSON" | jq '.'
echo ""
echo "解析后的字段:"
echo "  response: $(echo "$INPUT_JSON" | jq -r '.response')"
echo "  duration: $(echo "$INPUT_JSON" | jq -r '.duration_ms')ms"
echo "  timestamp: $(echo "$INPUT_JSON" | jq -r '.timestamp')"
EOF
chmod +x /tmp/demo_hook.sh

echo '{"response":"Task completed successfully","duration_ms":1234,"timestamp":"2025-12-14T10:30:00Z"}' | \
  /tmp/demo_hook.sh stop

echo ""

# 演示 5: 对比命令行参数 vs stdin
echo "演示 5: 为什么使用 stdin 而不是命令行参数？"
echo "----------------------------------------"
echo ""
echo "方式 1: 命令行参数（不推荐）"
echo "  ./script.sh '{\"data\":\"value\"}'"
echo "  问题: 有长度限制，需要转义，在 ps 中可见"
echo ""
echo "方式 2: stdin（推荐）"
echo "  echo '{\"data\":\"value\"}' | ./script.sh"
echo "  优势: 无长度限制，无需转义，不在 ps 中暴露"
echo ""

# 演示 6: 实际测试我们的 notify-telegram-smart.sh
echo "演示 6: 测试实际的 notify-telegram-smart.sh"
echo "----------------------------------------"
if [ -f ".claude/notify-telegram-smart.sh" ]; then
  echo "发送测试数据到实际的 hook 脚本..."
  echo ""

  # 检查 webhook 服务器是否运行
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Webhook 服务器正在运行"
    echo ""
    echo "发送 Stop Hook 测试数据:"
    echo '{"response":"Demo test from stdin demonstration","duration_ms":999,"timestamp":"2025-12-14T18:30:00Z"}' | \
      ./.claude/notify-telegram-smart.sh stop

    echo ""
    echo "检查 webhook 服务器状态:"
    curl -s http://localhost:8000/health | jq '.'
  else
    echo "⚠️  Webhook 服务器未运行"
    echo "启动命令: TEST_MODE=1 python3 webhook_server.py"
  fi
else
  echo "⚠️  找不到 notify-telegram-smart.sh"
fi

echo ""
echo "=========================================="
echo "演示完成！"
echo "=========================================="
echo ""
echo "关键要点:"
echo "1. Claude Code 通过 stdin 发送 JSON 数据"
echo "2. 脚本使用 INPUT_JSON=\$(cat) 读取 stdin"
echo "3. 使用 jq 解析 JSON 数据"
echo "4. stdin 适合传递大量数据"
echo ""
echo "手动测试命令:"
echo "  echo '{\"response\":\"test\"}' | ./.claude/notify-telegram-smart.sh stop"
