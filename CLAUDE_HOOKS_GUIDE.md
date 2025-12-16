# Claude Code Hooks 配置指南

## 📋 什么是 Claude Code Hooks？

Claude Code hooks 是在特定事件发生时自动执行的脚本。当 Claude Code 完成任务、执行工具或运行子代理时，会触发相应的 hook，并通过 **stdin** 传递 JSON 格式的上下文数据。

## 🔧 Hook 类型

### 1. Stop Hook
**触发时机：** Claude Code 完成一个响应时

**接收的数据：**
```json
{
  "response": "Claude's actual response text here...",
  "timestamp": "2025-12-14T10:30:00Z",
  "duration_ms": 1234,
  "tool_calls": [...]
}
```

### 2. PostToolUse Hook
**触发时机：** 工具执行完成后（如 Bash, Read, Write, Edit）

**接收的数据：**
```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "ls -la",
    "description": "List files"
  },
  "tool_output": "total 48\ndrwxr-xr-x...",
  "timestamp": "2025-12-14T10:30:00Z"
}
```

### 3. SubagentStop Hook
**触发时机：** 子代理（如 Explore, Plan）完成任务时

**接收的数据：**
```json
{
  "subagent_type": "explore",
  "description": "Search for error handling",
  "result": "Found 3 files...",
  "duration_ms": 5678,
  "timestamp": "2025-12-14T10:30:00Z"
}
```

## 📁 配置文件位置

Claude Code 会在以下位置查找配置：

```
~/.claude/settings.json
```

**重要：** 配置文件必须放在用户主目录的 `.claude` 文件夹中。

## 🚀 配置步骤

### 步骤 1: 检查配置文件是否存在

```bash
ls -la ~/.claude/settings.json
```

### 步骤 2: 如果不存在，复制我们的配置

```bash
# 创建目录（如果不存在）
mkdir -p ~/.claude

# 复制配置文件
cp .claude/settings.json ~/.claude/settings.json

# 复制通知脚本
cp .claude/notify-telegram-smart.sh ~/.claude/notify-telegram-smart.sh

# 设置执行权限
chmod +x ~/.claude/notify-telegram-smart.sh
```

### 步骤 3: 如果已存在，手动合并配置

如果 `~/.claude/settings.json` 已经存在，需要手动添加 hooks 配置：

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "~/.claude/notify-telegram-smart.sh stop"
      }]
    }],

    "PostToolUse": [{
      "matcher": "Bash|Read|Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "~/.claude/notify-telegram-smart.sh tool_use"
      }]
    }],

    "SubagentStop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "~/.claude/notify-telegram-smart.sh subagent"
      }]
    }]
  }
}
```

## 🧪 验证配置

### 1. 检查脚本是否可执行

```bash
ls -la ~/.claude/notify-telegram-smart.sh
# 应该显示 -rwxr-xr-x (有执行权限)
```

### 2. 手动测试脚本

```bash
echo '{"response":"test","duration_ms":123}' | ~/.claude/notify-telegram-smart.sh stop
```

**预期结果：**
- 脚本执行成功（退出码 0）
- 在 `~/.claude/hooks.log` 中看到日志
- 如果 webhook 服务器在运行，应该收到请求

### 3. 检查日志

```bash
# 查看 hook 执行日志
tail -f ~/.claude/hooks.log

# 查看最后的输出
cat ~/.claude/last_output.json
```

## 🔍 工作原理

```
┌─────────────────┐
│  Claude Code    │
│  执行任务       │
└────────┬────────┘
         │
         │ 触发 Stop Hook
         ▼
┌─────────────────────────────────────┐
│  ~/.claude/notify-telegram-smart.sh │
│  - 接收 JSON (通过 stdin)           │
│  - 解析事件类型                     │
│  - 格式化消息                       │
└────────┬────────────────────────────┘
         │
         │ HTTP POST
         ▼
┌─────────────────────────────────────┐
│  webhook_server.py                  │
│  - 接收 hook 数据                   │
│  - 存储到内存                       │
│  - 发送到 Telegram (或测试模式)     │
└─────────────────────────────────────┘
```

## 🐛 故障排查

### Hook 没有触发

**检查 1: 配置文件位置**
```bash
# 必须在这个位置
ls ~/.claude/settings.json
```

**检查 2: 脚本权限**
```bash
chmod +x ~/.claude/notify-telegram-smart.sh
```

**检查 3: 脚本路径**
```bash
# 在 settings.json 中使用绝对路径
"command": "~/.claude/notify-telegram-smart.sh stop"
# 或
"command": "/home/username/.claude/notify-telegram-smart.sh stop"
```

### Hook 执行但没有输出

**检查日志：**
```bash
tail -f ~/.claude/hooks.log
```

**检查 webhook 服务器：**
```bash
# 确保服务器在运行
curl http://localhost:8000/health
```

### JSON 解析错误

**测试 jq 是否安装：**
```bash
echo '{"test":"value"}' | jq '.'
```

如果没有安装：
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq
```

## 📊 测试 Claude Code 集成

### 完整测试流程

1. **启动 webhook 服务器（测试模式）：**
   ```bash
   TEST_MODE=1 python3 webhook_server.py
   ```

2. **在 Claude Code 中执行简单任务：**
   ```
   用户: echo "hello"
   ```

3. **检查 webhook 日志：**
   ```bash
   tail -f logs/webhook.log
   ```

4. **应该看到：**
   - `Received Claude hook: stop`
   - `[TEST MODE] Would send to Telegram: ...`
   - 包含实际的 Claude 响应内容

### 验证成功标准

- ✅ Hook 脚本被触发
- ✅ JSON 数据正确传递
- ✅ Webhook 服务器接收到数据
- ✅ 数据被正确解析和格式化
- ✅ 日志中包含完整的响应内容

## 🎯 下一步

配置成功后：

1. **本地测试完成** → 继续使用 `TEST_MODE=1`
2. **准备好 Telegram 集成** → 移除 `TEST_MODE`，使用真实的 Telegram API
3. **部署到生产** → 参考 `docs/prds/step1_connect.md` 的 Stage 2

## 📚 相关文件

- `.claude/settings.json` - Hook 配置示例
- `.claude/notify-telegram-smart.sh` - 通知脚本
- `tests/test_local_only.sh` - 本地测试脚本
- `webhook_server.py` - Webhook 服务器
