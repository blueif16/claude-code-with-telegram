# Stage 1 快速启动指南

## 前提条件检查

```bash
# 确保所有工具已安装
which python3 jq tmux curl
# 应该显示所有工具的路径

# 确保在项目目录
cd /mnt/c/Users/ran/Desktop/claude_code_telegram
```

## 启动步骤

### 1. 启动 Webhook 服务器

#### 测试模式（不实际发送 Telegram 消息）
```bash
TEST_MODE=1 python3 webhook_server.py
```

#### 生产模式（实际发送 Telegram 消息）
```bash
python3 webhook_server.py
```

服务器启动后会显示：
```
🧪 TEST MODE ENABLED - Telegram API calls will be simulated
Starting webhook server...
* Running on http://127.0.0.1:8000
```

### 2. 验证服务器运行（新终端）

```bash
curl http://localhost:8000/health | jq '.'
```

预期输出：
```json
{
  "last_outputs": {
    "stop": false,
    "subagent": false,
    "tool_use": false
  },
  "status": "ok",
  "timestamp": "2025-12-14T18:00:00.000000"
}
```

### 3. 运行本地测试

```bash
./tests/test_local_only.sh
```

预期结果：所有测试通过 ✅

### 4. 手动测试 Hook

```bash
# 测试 Stop Hook
echo '{"response":"Test completed","duration_ms":1234,"timestamp":"2025-12-14T10:30:00Z"}' | \
  ./.claude/notify-telegram-smart.sh stop

# 测试 Tool Use Hook
echo '{"tool_name":"Bash","tool_input":{"command":"ls"},"tool_output":"file1 file2"}' | \
  ./.claude/notify-telegram-smart.sh tool_use

# 测试 Subagent Hook
echo '{"subagent_type":"explore","description":"Search files","result":"Found 5 files","duration_ms":2000}' | \
  ./.claude/notify-telegram-smart.sh subagent
```

### 5. 创建 Tmux Session

```bash
# 创建 session
tmux new-session -d -s claude

# 验证
tmux list-sessions | grep claude

# 测试命令发送
tmux send-keys -t claude "echo 'Hello from Claude'" C-m

# 查看输出
tmux capture-pane -t claude -p | tail -5
```

## 与 Claude Code 集成

### 方法 1: 项目本地配置（推荐）

Claude Code 会自动读取项目目录下的 `.claude/settings.json`，无需额外配置。

### 方法 2: 全局配置

如果需要在其他项目中也使用这些 hooks：

```bash
# 备份现有配置（如果有）
cp ~/.claude/settings.json ~/.claude/settings.json.backup

# 复制项目配置
cp .claude/settings.json ~/.claude/settings.json

# 注意：需要修改路径为绝对路径
```

## 测试 Claude Code Hooks

1. 确保 webhook 服务器正在运行
2. 在 Claude Code 中执行任何任务
3. 任务完成后，检查：
   - Webhook 服务器控制台输出
   - `logs/webhook.log` 文件
   - Telegram 消息（如果是生产模式）

## 验证清单

- [ ] Webhook 服务器成功启动
- [ ] Health endpoint 返回正常
- [ ] 本地测试全部通过
- [ ] Hook 脚本可以手动执行
- [ ] Tmux session 创建成功
- [ ] 可以向 tmux 发送命令
- [ ] 日志文件正常记录

## 常用命令

### 查看日志
```bash
# Webhook 日志
tail -f logs/webhook.log

# Hook 日志
tail -f ~/.claude/hooks.log

# 实时查看（如果有）
tail -f ~/.claude/last_output.json
```

### 管理 Tmux
```bash
# 列出所有 sessions
tmux list-sessions

# 附加到 session
tmux attach -t claude

# 分离（在 tmux 内）
Ctrl+B, 然后按 D

# 杀死 session
tmux kill-session -t claude
```

### 测试 Telegram API（生产模式）
```bash
./tests/test_telegram.sh
```

## 故障排查

### 端口 8000 被占用
```bash
# 查找占用进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

### Hook 脚本没有执行权限
```bash
chmod +x .claude/notify-telegram-smart.sh
chmod +x tests/*.sh
```

### jq 命令未找到
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq
```

### Webhook 服务器无响应
```bash
# 检查进程
ps aux | grep webhook_server.py

# 重启服务器
pkill -f webhook_server.py
python3 webhook_server.py
```

## 下一步

Stage 1 完成后，可以进入 Stage 2：
- 安装 Cloudflare Tunnel
- 配置公网访问
- 设置 Telegram Webhook
- 实现远程控制

详见 `docs/prds/step1_connect.md` 的 Stage 2 部分。
