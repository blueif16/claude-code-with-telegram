# Tmux Deployment for Claude Code + Telegram System

## 目的
在 tmux 中部署完整的 Claude Code + Telegram webhook 系统，实现真正的后台运行和非阻塞交互。

## 核心问题

### AskUserQuestion 阻塞问题
当 Claude Code 在主终端运行时：
- AskUserQuestion 会阻塞 UI，等待用户输入
- 即使用户在 Telegram 中回答，主终端仍然卡在问题界面
- 答案通过 webhook → tmux 传递，但主终端无法感知

### Tmux 解决方案
在 tmux 中运行 Claude Code：
- Claude Code 在独立的 tmux session 中运行
- AskUserQuestion 在 tmux 中等待输入
- Telegram 回答通过 `tmux send-keys` 直接注入到 session
- 主终端可以自由操作，不受阻塞影响

## 部署架构

```
tmux session: webhook-server
├─ window 0: webhook_server.py (Flask)
└─ 监听 8000 端口

tmux session: claude
├─ window 0: Claude Code 主进程
└─ 接收来自 webhook 的输入

tmux session: cloudflare-tunnel
├─ window 0: cloudflared tunnel run
└─ 公网访问隧道
```

## 执行步骤

### 1. 启动 Webhook 服务器

```bash
# 创建 webhook-server session
tmux new-session -d -s webhook-server

# 在 session 中启动服务器
tmux send-keys -t webhook-server "cd /Users/tk/Desktop/claude-code-with-telegram" C-m
tmux send-keys -t webhook-server "python3 webhook_server.py" C-m

# 验证服务器启动
sleep 2
curl http://localhost:8000/health
```

### 2. 启动 Cloudflare Tunnel

```bash
# 创建 cloudflare-tunnel session
tmux new-session -d -s cloudflare-tunnel

# 启动 tunnel
tmux send-keys -t cloudflare-tunnel "cloudflared tunnel run claude-bot" C-m

# 验证 tunnel 连接
sleep 3
curl https://claude-bot.blueif.me/health
```

### 3. 启动 Claude Code

```bash
# 创建 claude session
tmux new-session -d -s claude

# 进入项目目录
tmux send-keys -t claude "cd /Users/tk/Desktop/claude-code-with-telegram" C-m

# 启动 Claude Code
tmux send-keys -t claude "claude" C-m
```

### 4. 监控和管理

```bash
# 查看所有 sessions
tmux list-sessions

# 附加到 webhook 服务器查看日志
tmux attach -t webhook-server

# 附加到 Claude Code 查看交互
tmux attach -t claude

# 附加到 tunnel 查看连接状态
tmux attach -t cloudflare-tunnel

# 分离当前 session（不关闭）
Ctrl+B, D

# 捕获 session 输出（不附加）
tmux capture-pane -t claude -p

# 发送命令到 session
tmux send-keys -t claude "echo test" C-m
```

### 5. 停止服务

```bash
# 停止单个 session
tmux kill-session -t webhook-server
tmux kill-session -t claude
tmux kill-session -t cloudflare-tunnel

# 或者停止所有相关 sessions
tmux kill-session -t webhook-server
tmux kill-session -t claude
tmux kill-session -t cloudflare-tunnel
```

## 完整部署脚本

创建 `start_all.sh`:

```bash
#!/bin/bash

PROJECT_DIR="/Users/tk/Desktop/claude-code-with-telegram"

echo "🚀 Starting Claude Code + Telegram system in tmux..."

# 1. 启动 webhook 服务器
echo "📡 Starting webhook server..."
tmux new-session -d -s webhook-server
tmux send-keys -t webhook-server "cd $PROJECT_DIR" C-m
tmux send-keys -t webhook-server "python3 webhook_server.py" C-m
sleep 2

# 验证 webhook
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Webhook server started"
else
    echo "❌ Webhook server failed to start"
    exit 1
fi

# 2. 启动 Cloudflare tunnel
echo "🌐 Starting Cloudflare tunnel..."
tmux new-session -d -s cloudflare-tunnel
tmux send-keys -t cloudflare-tunnel "cloudflared tunnel run claude-bot" C-m
sleep 3

# 验证 tunnel
if curl -s https://claude-bot.blueif.me/health > /dev/null; then
    echo "✅ Cloudflare tunnel connected"
else
    echo "⚠️  Cloudflare tunnel may need more time to connect"
fi

# 3. 启动 Claude Code
echo "🤖 Starting Claude Code..."
tmux new-session -d -s claude
tmux send-keys -t claude "cd $PROJECT_DIR" C-m
tmux send-keys -t claude "claude" C-m

echo ""
echo "✅ All services started!"
echo ""
echo "📋 Available sessions:"
tmux list-sessions
echo ""
echo "💡 Usage:"
echo "  - Attach to Claude Code:    tmux attach -t claude"
echo "  - Attach to webhook server: tmux attach -t webhook-server"
echo "  - Attach to tunnel:         tmux attach -t cloudflare-tunnel"
echo "  - Detach from session:      Ctrl+B, D"
echo "  - View logs:                tail -f logs/webhook.log"
```

创建 `stop_all.sh`:

```bash
#!/bin/bash

echo "🛑 Stopping all services..."

# 停止所有 sessions
tmux kill-session -t webhook-server 2>/dev/null && echo "✅ Webhook server stopped"
tmux kill-session -t claude 2>/dev/null && echo "✅ Claude Code stopped"
tmux kill-session -t cloudflare-tunnel 2>/dev/null && echo "✅ Cloudflare tunnel stopped"

echo ""
echo "✅ All services stopped"
```

使用方法：

```bash
# 启动所有服务
chmod +x start_all.sh stop_all.sh
./start_all.sh

# 停止所有服务
./stop_all.sh
```

## AskUserQuestion 非阻塞交互

### 问题分析

**主终端运行时**：
```
User → Claude Code (主终端)
         ↓
    AskUserQuestion 触发
         ↓
    UI 阻塞，等待输入
         ↓
    Telegram 回答 → Webhook → Tmux send-keys
         ↓
    ❌ 主终端仍然阻塞（因为不在 tmux 中）
```

**Tmux 运行时**：
```
User → Claude Code (tmux session "claude")
         ↓
    AskUserQuestion 触发
         ↓
    Tmux session 等待输入（不阻塞主终端）
         ↓
    Telegram 回答 → Webhook → tmux send-keys -t claude
         ↓
    ✅ 答案直接注入到 tmux session
         ↓
    ✅ Claude Code 接收到输入，继续执行
```

### 正确的交互方式

**通过 tmux send-keys 向 claude session 发送命令**：

```bash
# 发送命令让 Claude Code 执行任务（会触发 AskUserQuestion）
tmux send-keys -t claude 'claude "ask me which language I prefer and explain why"' C-m

# 持续监控 claude session 输出
tmux capture-pane -t claude -p | tail -50

# 监控 webhook 日志查看问题发送和回调
tail -f logs/webhook.log | grep -E "question|callback|inline_keyboard"
```

**完整测试流程**：

1. **发送测试命令到 claude session**
```bash
tmux send-keys -t claude 'claude "ask user a question and respond based on answer"' C-m
```

2. **监控 claude session 状态**
```bash
# 每隔几秒查看输出
sleep 3 && tmux capture-pane -t claude -p
```

3. **检查 webhook 日志**
```bash
# 确认问题已发送到 Telegram
tail -20 logs/webhook.log | grep "Question prompt sent"
```

4. **在 Telegram 点击按钮回答**
   - 用户在 Telegram 中点击 inline keyboard 按钮

5. **验证答案回传**
```bash
# 查看 webhook 收到 callback 并发送到 tmux
tail -20 logs/webhook.log | grep "Received callback"

# 查看 claude session 收到答案
tmux capture-pane -t claude -p | grep "User answered"
```

6. **确认 Claude Code 基于答案继续执行**
```bash
# 查看完整响应
tmux capture-pane -t claude -p
```

## 高级用法

### 多窗口布局

在单个 session 中运行多个服务：

```bash
# 创建 session 并命名第一个窗口
tmux new-session -d -s claude-system -n webhook

# 在第一个窗口启动 webhook
tmux send-keys -t claude-system:webhook "cd $PROJECT_DIR && python3 webhook_server.py" C-m

# 创建第二个窗口运行 tunnel
tmux new-window -t claude-system -n tunnel
tmux send-keys -t claude-system:tunnel "cloudflared tunnel run claude-bot" C-m

# 创建第三个窗口运行 Claude Code
tmux new-window -t claude-system -n claude
tmux send-keys -t claude-system:claude "cd $PROJECT_DIR && claude" C-m

# 附加到 session（默认显示第一个窗口）
tmux attach -t claude-system

# 在 session 中切换窗口
# Ctrl+B, 0  → webhook 窗口
# Ctrl+B, 1  → tunnel 窗口
# Ctrl+B, 2  → claude 窗口
```

### 分屏布局

在单个窗口中同时查看多个服务：

```bash
# 创建 session
tmux new-session -d -s claude-system

# 水平分屏
tmux split-window -h -t claude-system

# 在左侧运行 webhook
tmux send-keys -t claude-system.0 "cd $PROJECT_DIR && python3 webhook_server.py" C-m

# 在右侧运行 Claude Code
tmux send-keys -t claude-system.1 "cd $PROJECT_DIR && claude" C-m

# 附加查看
tmux attach -t claude-system

# 在 session 中切换 pane
# Ctrl+B, 方向键
```

### 日志监控

创建专门的日志监控窗口：

```bash
tmux new-window -t claude-system -n logs
tmux send-keys -t claude-system:logs "tail -f logs/webhook.log" C-m
```

## 故障排查

### Session 已存在
```bash
# 错误：session already exists
# 解决：先删除旧 session
tmux kill-session -t claude
tmux new-session -d -s claude
```

### 无法连接到 tmux server
```bash
# 检查 tmux 是否运行
ps aux | grep tmux

# 重启 tmux server
tmux kill-server
tmux new-session -d -s test
```

### Webhook 未收到 callback
```bash
# 检查 webhook 日志
tail -f logs/webhook.log

# 检查 Telegram webhook 配置
curl -s "https://api.telegram.org/bot<TOKEN>/getWebhookInfo" | python3 -m json.tool

# 测试 tunnel 连接
curl https://claude-bot.blueif.me/health
```

### Claude Code 未收到答案
```bash
# 检查 tmux session 名称
tmux list-sessions | grep claude

# 检查 config.json 中的 tmux_session 配置
grep tmux_session config.json

# 手动测试 tmux send-keys
tmux send-keys -t claude "test message" C-m
tmux capture-pane -t claude -p
```

## 工具
- Bash
- Read
- Write
