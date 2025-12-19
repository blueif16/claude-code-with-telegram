# 🚀 Claude Code Telegram Bot - Quick Start Guide

## 🎯 What You Can Do Now (Stage 3 Complete!)

You can now **control Claude Code entirely from Telegram**:
- ✅ Send tasks from anywhere (no terminal access needed)
- ✅ Auto-start Claude Code sessions
- ✅ Real-time progress notifications
- ✅ Monitor remotely from your phone

## 📋 Project Files

```
claude_code_telegram/
├── config.json                      # 配置文件（需要编辑）
├── requirements.txt                 # Python 依赖
├── webhook_server.py                # Webhook 服务器
├── PHASE1_CHECKLIST.md             # 详细检查清单
├── QUICKSTART.md                   # 本文件
├── .claude/
│   ├── notify-telegram-smart.sh    # 智能通知脚本
│   └── settings.json               # Claude Code hooks 配置
├── logs/                           # 日志目录（自动创建）
└── tests/
    ├── test_hook.sh                # Hook 测试
    ├── test_webhook.sh             # Webhook 测试
    └── test_telegram.sh            # Telegram API 测试
```

## 🚀 快速开始（3 步）

### 1️⃣ 运行自动设置脚本

```bash
./setup.sh
```

这个脚本会自动：
- ✅ 检测系统（macOS 或 WSL/Linux）
- ✅ 安装 tmux（如果未安装）
- ✅ 检查 Python、jq 等依赖
- ✅ 安装 Python 依赖包
- ✅ 生成正确路径的 settings.json
- ✅ 设置文件权限

**支持的系统：**
- macOS（使用 Homebrew）
- WSL（Windows Subsystem for Linux）
- Linux（使用 apt）

### 2️⃣ 配置 Telegram Bot

编辑 `config.json`，填写以下信息：

```json
{
  "telegram": {
    "bot_token": "你的_BOT_TOKEN",      // 从 @BotFather 获取
    "chat_id": "你的_CHAT_ID",          // 见下方获取方法
    "secret_token": "随机字符串"         // 改成任意随机字符串
  }
}
```

**获取 Chat ID：**
1. 打开 Telegram，搜索你的 bot
2. 发送任意消息（如 "hello"）
3. 访问：`https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. 在 JSON 中找到 `message.chat.id`

### 3️⃣ 启动并测试

**启动 Webhook 服务器：**
```bash
python3 webhook_server.py
```

应该看到：
```
INFO Starting webhook server...
 * Running on http://127.0.0.1:8000
```

**测试 Telegram 连接：**
```bash
./tests/test_telegram.sh
```

**在 Telegram 中测试：**
- 发送 `/help` - 应该收到帮助信息
- 发送 `/ask 列出当前目录的文件` - Claude Code 会自动启动并执行任务

## ✅ 验证成功标准

- [ ] `test_telegram.sh` 全部通过
- [ ] `test_hook.sh` 发送后 Telegram 收到 3 条消息
- [ ] `test_webhook.sh` 全部通过
- [ ] Telegram 发送 `/help` 收到响应
- [ ] Telegram 发送 `/status` 收到 tmux 输出
- [ ] 日志文件正常生成（`logs/webhook.log`）

## 🔧 跨平台使用

**在不同机器上使用：**

1. 克隆或复制项目到新机器
2. 运行 `./setup.sh` - 会自动适配当前系统和路径
3. 编辑 `config.json` 填入 Telegram 凭证
4. 启动服务器

**支持的平台：**
- ✅ macOS（已测试）
- ✅ WSL（Windows Subsystem for Linux）
- ✅ Linux

setup.sh 会自动：
- 检测操作系统
- 安装缺失的依赖（tmux、jq）
- 生成适配当前路径的 settings.json
- 设置正确的文件权限

## 📊 测试 Claude Code 集成

1. 启动 webhook 服务器（如果还没启动）
2. 在 Claude Code 中执行任意任务
3. 任务完成时应该收到 Telegram 通知

## 🚨 常见问题

### Telegram 收不到消息
```bash
# 检查 bot token 和 chat_id
./tests/test_telegram.sh
```

### Webhook 无法启动
```bash
# 检查端口是否被占用
lsof -i :8000

# 查看日志
tail -f logs/webhook.log
```

### Hook 没有触发
```bash
# 检查脚本权限
ls -la .claude/notify-telegram-smart.sh

# 手动测试
echo '{"response":"test"}' | ./.claude/notify-telegram-smart.sh stop
```

## 📱 New Commands (Stage 3)

### Interactive Session Commands

**`/ask <task>`** - Send a task to Claude Code (auto-starts if needed)
```
Examples:
/ask Analyze the webhook_server.py file
/ask List all Python files in this project
/ask Explain how the hooks system works
```

**`/session`** - Check Claude Code session status

**`/start_claude`** - Manually start Claude Code session

**`/stop_claude`** - Stop Claude Code session

### Monitoring Commands

**`/status`** - Get last 20 lines of tmux output

**`/last_output`** - Get full last response from Claude Code

**`/help`** - Show all available commands

## 🎯 Typical Workflow

1. **Send a task from Telegram:**
   ```
   /ask What files are in the logs directory?
   ```

2. **System auto-starts Claude Code** (if not running)

3. **Receive progress notifications:**
   - Tool executions
   - Task completion
   - Results

4. **View full output:**
   ```
   /last_output
   ```

## 🧪 Testing Stage 3

Run the comprehensive test:
```bash
./tests/test_interactive_session.sh
```

Check your Telegram app for results!

## 📚 Documentation

- **Stage 1 (Local Setup)**: `docs/prds/step1_connect.md`
- **Stage 2 (Public Access)**: `docs/prds/step2_public_access.md`
- **Stage 3 (Interactive Sessions)**: `docs/prds/step3_interactive_session.md`
- **Project Overview**: `CLAUDE.md`

## 🔗 有用的命令

```bash
# 查看 webhook 日志
tail -f logs/webhook.log

# 查看 hook 日志
tail -f ~/.claude/hooks.log

# 检查 webhook 健康状态
curl http://localhost:8000/health

# 停止 webhook 服务器
pkill -f webhook_server.py

# 查看 tmux session
tmux list-sessions
```
