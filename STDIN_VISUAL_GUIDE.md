# stdin 机制可视化指南

## 核心问题：谁发送 JSON 到 .sh 文件？

**答案：Claude Code 本身**

## 可视化流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code 内部                             │
│                                                                  │
│  1. 用户执行任务: "帮我分析这个日志文件"                          │
│                                                                  │
│  2. Claude Code 处理任务...                                      │
│                                                                  │
│  3. 任务完成 ✅                                                  │
│                                                                  │
│  4. 触发 Stop Hook 事件                                          │
│                                                                  │
│  5. 准备 JSON 数据:                                              │
│     {                                                            │
│       "response": "分析完成，发现 3 个错误...",                   │
│       "duration_ms": 5432,                                       │
│       "timestamp": "2025-12-14T10:30:00Z"                        │
│     }                                                            │
│                                                                  │
│  6. 查找配置的 hook command:                                     │
│     "/path/to/notify-telegram-smart.sh stop"                    │
│                                                                  │
│  7. 执行命令并将 JSON 通过 stdin 传递                            │
│     (类似于: echo '...' | script.sh)                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ stdin (标准输入流)
                            │ 传递 JSON 数据
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              notify-telegram-smart.sh 脚本                       │
│                                                                  │
│  #!/bin/bash                                                     │
│                                                                  │
│  # 第 1 步: 获取事件类型（命令行参数）                           │
│  EVENT_TYPE="$1"  # 值为 "stop"                                 │
│                                                                  │
│  # 第 2 步: 从 stdin 读取 JSON 数据                              │
│  INPUT_JSON=$(cat)  # ← 这里读取 Claude Code 发送的 JSON        │
│                                                                  │
│  # 第 3 步: 解析 JSON                                            │
│  RESPONSE=$(echo "$INPUT_JSON" | jq -r '.response')             │
│  DURATION=$(echo "$INPUT_JSON" | jq -r '.duration_ms')          │
│  TIMESTAMP=$(echo "$INPUT_JSON" | jq -r '.timestamp')           │
│                                                                  │
│  # 第 4 步: 格式化消息                                           │
│  MESSAGE="✅ *Task Completed*                                    │
│  *Duration:* ${DURATION}ms                                       │
│  *Response:* ${RESPONSE}"                                        │
│                                                                  │
│  # 第 5 步: 发送到 webhook                                       │
│  curl -X POST http://localhost:8000/claude-hook \               │
│    -d "{\"event\":\"$EVENT_TYPE\",\"message\":\"$MESSAGE\"}"     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP POST
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Webhook 服务器                                  │
│                  (webhook_server.py)                             │
│                                                                  │
│  1. 接收 POST 请求                                               │
│  2. 存储数据到内存                                               │
│  3. 调用 Telegram API                                            │
│  4. 发送消息                                                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Telegram API
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    你的 Telegram                                 │
│                                                                  │
│  📱 收到通知:                                                    │
│                                                                  │
│  ✅ Task Completed                                               │
│  Duration: 5432ms                                                │
│  Response: 分析完成，发现 3 个错误...                            │
└─────────────────────────────────────────────────────────────────┘
```

## stdin 是什么？

### 类比 1: 水管系统

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│ 水龙头   │ ═══════>│   水管   │ ═══════>│   水桶   │
│(数据源)  │         │ (stdin)  │         │ (脚本)   │
└──────────┘         └──────────┘         └──────────┘
Claude Code          标准输入流           notify-telegram
发送 JSON                                 -smart.sh
```

### 类比 2: 邮递系统

```
发件人 (Claude Code)
    ↓ 写信 (生成 JSON)
    ↓ 放入信封 (stdin)
    ↓ 邮递员传递
    ↓
收件人 (notify-telegram-smart.sh)
    ↓ 打开信封 (cat 命令)
    ↓ 阅读内容 (解析 JSON)
    ↓ 采取行动 (发送到 webhook)
```

## 命令行等价操作

### Claude Code 内部做的事情

```bash
# 伪代码
json_data='{"response":"Task completed","duration_ms":1234,"timestamp":"2025-12-14T10:30:00Z"}'
command="/path/to/notify-telegram-smart.sh stop"

# 执行命令并通过 stdin 传递数据
echo "$json_data" | $command
```

### 你可以手动模拟

```bash
# 完全相同的操作
echo '{"response":"Task completed","duration_ms":1234,"timestamp":"2025-12-14T10:30:00Z"}' | \
  ./.claude/notify-telegram-smart.sh stop
```

## 脚本如何读取 stdin

### 关键代码

```bash
#!/bin/bash

# 方法 1: 使用 cat 命令
INPUT_JSON=$(cat)

# 方法 2: 使用 read 命令（逐行读取）
while IFS= read -r line; do
  INPUT_JSON="$INPUT_JSON$line"
done

# 方法 3: 使用 stdin 重定向
INPUT_JSON=$(< /dev/stdin)
```

### 我们使用的方法

```bash
# notify-telegram-smart.sh 第 9 行
INPUT_JSON=$(cat)
```

**解释**：
- `cat` 命令读取 stdin 的所有内容
- `$()` 将读取的内容赋值给变量
- `INPUT_JSON` 现在包含完整的 JSON 字符串

## 为什么使用 stdin？

### 对比表

| 特性 | 命令行参数 | stdin |
|------|-----------|-------|
| 长度限制 | ❌ 有限制（几千字符） | ✅ 无限制 |
| 特殊字符 | ❌ 需要转义 | ✅ 无需转义 |
| 安全性 | ❌ 在 `ps` 中可见 | ✅ 不可见 |
| 适用场景 | 短参数 | 大量数据 |

### 示例对比

#### 方式 1: 命令行参数（不推荐）

```bash
# ❌ 问题多
./script.sh '{"response":"Very long text that could exceed limits and needs escaping for special chars like \" and \'"}'

# 在进程列表中可见
ps aux | grep script.sh
# 会显示完整的参数，包括敏感数据
```

#### 方式 2: stdin（推荐）

```bash
# ✅ 更好
echo '{"response":"Very long text..."}' | ./script.sh

# 在进程列表中只显示命令
ps aux | grep script.sh
# 只显示: ./script.sh
```

## 实际测试

### 测试 1: 基本 stdin 读取

```bash
# 创建测试脚本
cat > test.sh << 'EOF'
#!/bin/bash
DATA=$(cat)
echo "Received: $DATA"
EOF

chmod +x test.sh

# 测试
echo "Hello World" | ./test.sh
# 输出: Received: Hello World
```

### 测试 2: JSON 解析

```bash
# 测试 JSON 解析
echo '{"name":"Alice","age":30}' | jq -r '.name'
# 输出: Alice

# 在脚本中使用
cat > parse.sh << 'EOF'
#!/bin/bash
JSON=$(cat)
NAME=$(echo "$JSON" | jq -r '.name')
AGE=$(echo "$JSON" | jq -r '.age')
echo "Name: $NAME, Age: $AGE"
EOF

chmod +x parse.sh
echo '{"name":"Bob","age":25}' | ./parse.sh
# 输出: Name: Bob, Age: 25
```

### 测试 3: 实际的 hook 脚本

```bash
# 启动 webhook 服务器
TEST_MODE=1 python3 webhook_server.py &

# 等待启动
sleep 2

# 测试 Stop Hook
echo '{
  "response": "Test task completed",
  "duration_ms": 1234,
  "timestamp": "2025-12-14T10:30:00Z"
}' | ./.claude/notify-telegram-smart.sh stop

# 检查结果
curl http://localhost:8000/health | jq '.'
```

## 常见问题

### Q1: Claude Code 如何知道要执行哪个命令？

**A**: 从 `.claude/settings.json` 配置文件中读取：

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "/path/to/notify-telegram-smart.sh stop"
      }]
    }]
  }
}
```

### Q2: JSON 数据是如何传递的？

**A**: Claude Code 将 JSON 写入命令的 stdin，就像这样：

```bash
echo '{"response":"..."}' | /path/to/script.sh
```

### Q3: 脚本如何知道接收到了数据？

**A**: 脚本使用 `$(cat)` 读取 stdin：

```bash
INPUT_JSON=$(cat)  # 阻塞等待，直到读取完所有数据
```

### Q4: 如果 JSON 很大怎么办？

**A**: stdin 没有大小限制，可以传递任意大小的数据。这就是为什么使用 stdin 而不是命令行参数。

### Q5: 如何调试 stdin 数据？

**A**: 在脚本中添加日志：

```bash
#!/bin/bash
INPUT_JSON=$(cat)

# 保存到文件以便调试
echo "$INPUT_JSON" > /tmp/debug_stdin.json
echo "$(date): Received JSON" >> /tmp/debug.log
echo "$INPUT_JSON" >> /tmp/debug.log

# 继续处理...
```

## 总结

### 关键要点

1. **谁发送？** Claude Code 本身
2. **如何发送？** 通过 stdin（标准输入流）
3. **如何接收？** 脚本使用 `INPUT_JSON=$(cat)` 读取
4. **为什么这样？** stdin 适合传递大量数据，无长度限制
5. **如何测试？** 使用 `echo '...' | script.sh` 手动模拟

### 数据流总结

```
Claude Code → stdin → notify-telegram-smart.sh → webhook → Telegram
   (发送)    (传输)        (接收并处理)         (转发)    (显示)
```

### 验证理解

运行演示脚本：
```bash
./demo_stdin.sh
```

这个脚本会展示 stdin 的各种用法，帮助你理解整个机制。
