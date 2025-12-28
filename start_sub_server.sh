#!/bin/bash

# 在 tmux 会话中启动子 webhook 服务器
# 用法: ./start_sub_server.sh <tmux_session> <port>

if [ $# -lt 2 ]; then
    echo "用法: $0 <tmux_session> <port>"
    echo "示例: $0 claude 8001"
    exit 1
fi

TMUX_SESSION=$1
PORT=$2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== 启动子 Webhook 服务器 ==="
echo "Tmux 会话: $TMUX_SESSION"
echo "端口: $PORT"
echo ""

# 检查 tmux 会话是否存在
if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "✗ Tmux 会话 '$TMUX_SESSION' 不存在"
    echo ""
    echo "请先创建会话:"
    echo "  tmux new-session -s $TMUX_SESSION"
    exit 1
fi

echo "✓ Tmux 会话存在"

# 检查端口是否已被占用
if lsof -i ":$PORT" > /dev/null 2>&1; then
    echo "⚠️  端口 $PORT 已被占用"
    echo ""
    read -p "是否停止现有进程? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti ":$PORT" | xargs kill -9
        echo "✓ 已停止现有进程"
        sleep 1
    else
        echo "✗ 取消启动"
        exit 1
    fi
fi

# 在 tmux 会话中启动子服务器（在新窗口中）
echo "启动子服务器..."

tmux new-window -t "$TMUX_SESSION" -n "sub-server" \
    "cd '$SCRIPT_DIR' && python3 sub_webhook_server.py $PORT $TMUX_SESSION"

sleep 2

# 验证服务器是否启动
if curl -s "http://127.0.0.1:$PORT/health" > /dev/null; then
    echo "✓ 子服务器启动成功"
    echo ""
    echo "健康检查: http://127.0.0.1:$PORT/health"
    echo "日志文件: logs/sub_webhook_${TMUX_SESSION}.log"
    echo ""
    echo "查看日志:"
    echo "  tail -f logs/sub_webhook_${TMUX_SESSION}.log"
else
    echo "✗ 子服务器启动失败"
    echo ""
    echo "检查日志:"
    echo "  tail -f logs/sub_webhook_${TMUX_SESSION}.log"
    exit 1
fi
