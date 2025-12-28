#!/bin/bash

# 完整系统启动脚本

echo "=== Claude Code + Telegram 多项目系统启动 ==="
echo ""

# 1. 启动主 webhook 服务器
echo "1. 启动主 Webhook 服务器..."
if pgrep -f "webhook_server.py" > /dev/null; then
    echo "   ⚠️  主服务器已在运行"
else
    python3 webhook_server.py > /dev/null 2>&1 &
    sleep 3
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "   ✓ 主服务器启动成功 (端口 8000)"
    else
        echo "   ✗ 主服务器启动失败"
        exit 1
    fi
fi

echo ""

# 2. 读取项目配置并启动子服务器
echo "2. 启动子 Webhook 服务器..."

# 从 config.json 读取项目列表
PROJECTS=$(jq -r '.projects.list | to_entries[] | "\(.value.tmux_session):\(.value.sub_server_port)"' config.json)

if [ -z "$PROJECTS" ]; then
    echo "   ⚠️  未配置项目"
else
    while IFS=: read -r session port; do
        echo "   启动 $session 的子服务器 (端口 $port)..."

        # 检查 tmux 会话是否存在
        if ! tmux has-session -t "$session" 2>/dev/null; then
            echo "      ⚠️  Tmux 会话 '$session' 不存在，跳过"
            continue
        fi

        # 检查端口是否已被占用
        if lsof -i ":$port" > /dev/null 2>&1; then
            echo "      ⚠️  端口 $port 已被占用，跳过"
            continue
        fi

        # 启动子服务器
        ./start_sub_server.sh "$session" "$port" > /dev/null 2>&1

        if curl -s "http://localhost:$port/health" > /dev/null; then
            echo "      ✓ 子服务器启动成功"
        else
            echo "      ✗ 子服务器启动失败"
        fi
    done <<< "$PROJECTS"
fi

echo ""
echo "=== 启动完成 ==="
echo ""
echo "服务状态:"
echo "  主服务器: http://localhost:8000/health"
echo ""
echo "可用命令:"
echo "  /projects - 查看所有项目和子服务器状态"
echo "  直接发送消息 - 发送到当前项目的 Claude Code"
echo ""
echo "日志文件:"
echo "  主服务器: tail -f logs/webhook.log"
echo "  子服务器: tail -f logs/sub_webhook_*.log"
