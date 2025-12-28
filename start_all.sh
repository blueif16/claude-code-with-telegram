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
