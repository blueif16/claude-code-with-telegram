# stdin 机制详解

## 什么是 stdin？

stdin（标准输入）是 Unix/Linux 中程序接收输入的标准方式。

## 简单示例

### 示例 1: 基本的 stdin 使用

```bash
# cat 命令从 stdin 读取并输出
echo "Hello World" | cat
# 输出: Hello World
```

**解释**：
- `echo "Hello World"` 输出文本
- `|` 管道符将左边的输出传递给右边的输入
- `cat` 从 stdin 读取并显示

### 示例 2: 在脚本中读取 stdin

创建一个简单的脚本 `read_stdin.sh`：

```bash
#!/bin/bash
# 从 stdin 读取所有内容
DATA=$(cat)
echo "Received: $DATA"
```

使用：
```bash
echo "test data" | ./read_stdin.sh
# 输出: Received: test data
```

### 示例 3: 读取 JSON 数据

创建脚本 `parse_json.sh`：

```bash
#!/bin/bash
# 从 stdin 读取 JSON
JSON_DATA=$(cat)

# 使用 jq 解析
NAME=$(echo "$JSON_DATA" | jq -r '.name')
AGE=$(echo "$JSON_DATA" | jq -r '.age')

echo "Name: $NAME"
echo "Age: $AGE"
```

使用：
```bash
echo '{"name":"Alice","age":30}' | ./parse_json.sh
# 输出:
# Name: Alice
# Age: 30
```

## 我们的项目中如何使用

### Claude Code 的行为

当 Claude Code 触发 hook 时，它会：

```bash
# 伪代码表示 Claude Code 内部的操作
json_data = {
  "response": "Task completed",
  "duration_ms": 1234,
  "timestamp": "2025-12-14T10:30:00Z"
}

# 执行命令并将 JSON 通过 stdin 传递
execute_command_with_stdin(
  command="/path/to/notify-telegram-smart.sh stop",
  stdin_data=json_data
)
```

**等价于命令行操作**：
```bash
echo '{"response":"Task completed","duration_ms":1234,"timestamp":"2025-12-14T10:30:00Z"}' | \
  /path/to/notify-telegram-smart.sh stop
```

### notify-telegram-smart.sh 的处理

```bash
#!/bin/bash

# 第 1 步: 获取事件类型（从命令行参数）
EVENT_TYPE="$1"  # 值为 "stop"

# 第 2 步: 读取 JSON 数据（从 stdin）
INPUT_JSON=$(cat)  # 读取 Claude Code 传递的 JSON

# 第 3 步: 解析 JSON
RESPONSE=$(echo "$INPUT_JSON" | jq -r '.response')
DURATION=$(echo "$INPUT_JSON" | jq -r '.duration_ms')
TIMESTAMP=$(echo "$INPUT_JSON" | jq -r '.timestamp')

# 第 4 步: 格式化消息
MESSAGE="✅ *Task Completed*

*Duration:* ${DURATION}ms
*Time:* ${TIMESTAMP}

*Response Preview:*
\`\`\`
${RESPONSE}
\`\`\`"

# 第 5 步: 发送到 webhook
curl -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d "{\"event\":\"$EVENT_TYPE\",\"message\":\"$MESSAGE\",\"raw_data\":$INPUT_JSON}"
```

## 为什么使用 stdin 而不是命令行参数？

### 命令行参数的限制

```bash
# ❌ 不好的方式 - 参数可能很长
./script.sh '{"response":"Very long text that could exceed command line limits..."}'
```

**问题**：
1. 命令行参数有长度限制（通常几千字符）
2. 需要处理特殊字符转义
3. 在进程列表中可见（`ps aux` 可以看到）

### stdin 的优势

```bash
# ✅ 好的方式 - 通过 stdin 传递
echo '{"response":"Very long text..."}' | ./script.sh
```

**优势**：
1. 无长度限制
2. 不需要复杂的转义
3. 不会在进程列表中暴露数据
4. 更适合传递大量数据

## 实际测试

### 测试 1: 验证脚本可以读取 stdin

```bash
cd /mnt/c/Users/ran/Desktop/claude_code_telegram

# 启动 webhook 服务器（在另一个终端）
TEST_MODE=1 python3 webhook_server.py

# 发送测试数据
echo '{"response":"Test from stdin","duration_ms":123,"timestamp":"2025-12-14T10:30:00Z"}' | \
  ./.claude/notify-telegram-smart.sh stop
```

### 测试 2: 验证 JSON 解析

```bash
# 创建测试脚本
cat > test_stdin.sh << 'EOF'
#!/bin/bash
INPUT=$(cat)
echo "Received from stdin:"
echo "$INPUT" | jq '.'
EOF

chmod +x test_stdin.sh

# 测试
echo '{"name":"test","value":123}' | ./test_stdin.sh
```

### 测试 3: 模拟 Claude Code 的完整流程

```bash
# 1. 启动 webhook 服务器
TEST_MODE=1 python3 webhook_server.py &

# 2. 等待启动
sleep 2

# 3. 模拟 Stop Hook
echo '{
  "response": "I have completed the analysis. Found 3 issues.",
  "duration_ms": 5432,
  "timestamp": "2025-12-14T18:30:00Z"
}' | ./.claude/notify-telegram-smart.sh stop

# 4. 检查结果
curl http://localhost:8000/health | jq '.'

# 5. 查看日志
tail -10 logs/webhook.log
```

## 关键要点总结

1. **谁发送 JSON？**
   - Claude Code 本身在触发 hook 时自动发送

2. **如何发送？**
   - 通过 stdin（标准输入流）传递 JSON 数据

3. **脚本如何接收？**
   - 使用 `INPUT_JSON=$(cat)` 读取 stdin 的所有内容

4. **为什么这样设计？**
   - stdin 适合传递大量数据
   - 避免命令行参数长度限制
   - 更安全（不在进程列表中暴露）

5. **如何验证？**
   - 手动使用 `echo '...' | script.sh` 模拟
   - 查看脚本中的 `$(cat)` 代码
   - 运行测试脚本验证

## 类比理解

想象一下：
- **Claude Code** = 水龙头（数据源）
- **stdin** = 水管（传输通道）
- **notify-telegram-smart.sh** = 水桶（接收容器）
- **`$(cat)`** = 打开水桶接水的动作

当水龙头打开时，水通过水管流入水桶。脚本通过 `$(cat)` "接水"，获取所有流入的数据。
