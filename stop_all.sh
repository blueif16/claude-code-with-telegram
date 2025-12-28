#!/bin/bash

echo "🛑 Stopping all services..."

# 停止所有 sessions
tmux kill-session -t webhook-server 2>/dev/null && echo "✅ Webhook server stopped"
tmux kill-session -t claude 2>/dev/null && echo "✅ Claude Code stopped"
tmux kill-session -t cloudflare-tunnel 2>/dev/null && echo "✅ Cloudflare tunnel stopped"

echo ""
echo "✅ All services stopped"
