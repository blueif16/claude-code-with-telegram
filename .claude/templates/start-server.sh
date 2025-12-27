#!/bin/bash
# 服务器启动脚本
# 返回: 0=成功, 1=失败
# 输出: JSON 格式的启动结果

set -e

CONFIG_FILE="config.json"
PORT=$(jq -r '.webhook.port' "$CONFIG_FILE" 2>/dev/null || echo "8000")
HOST=$(jq -r '.webhook.host' "$CONFIG_FILE" 2>/dev/null || echo "127.0.0.1")

# 检查端口占用
check_port() {
    if lsof -i ":$PORT" &> /dev/null; then
        PID=$(lsof -ti ":$PORT")
        PROCESS=$(ps -p "$PID" -o comm= 2>/dev/null || echo "unknown")
        echo "{\"occupied\":true,\"port\":$PORT,\"pid\":$PID,\"process\":\"$PROCESS\"}"
        return 1
    else
        echo "{\"occupied\":false,\"port\":$PORT}"
        return 0
    fi
}

# 创建日志目录
mkdir -p logs

# 检查端口
PORT_CHECK=$(check_port)
if echo "$PORT_CHECK" | jq -e '.occupied' &> /dev/null; then
    cat <<EOF
{
  "success": false,
  "error": "端口已被占用",
  "port_info": $PORT_CHECK,
  "suggestion": "运行 'kill \$(lsof -ti :$PORT)' 终止现有进程",
  "exit_code": 1
}
EOF
    exit 1
fi

# 启动服务器（后台运行）
nohup python3 webhook_server.py > logs/server_startup.log 2>&1 &
SERVER_PID=$!

# 等待服务器启动
sleep 2

# 验证服务器是否运行
if ps -p $SERVER_PID > /dev/null; then
    # 健康检查
    if curl -s "http://$HOST:$PORT/health" > /dev/null 2>&1; then
        cat <<EOF
{
  "success": true,
  "pid": $SERVER_PID,
  "host": "$HOST",
  "port": $PORT,
  "health_url": "http://$HOST:$PORT/health",
  "log_file": "logs/webhook.log",
  "exit_code": 0
}
EOF
        exit 0
    else
        cat <<EOF
{
  "success": false,
  "error": "服务器启动但健康检查失败",
  "pid": $SERVER_PID,
  "suggestion": "检查 logs/server_startup.log",
  "exit_code": 1
}
EOF
        exit 1
    fi
else
    cat <<EOF
{
  "success": false,
  "error": "服务器进程启动失败",
  "suggestion": "检查 logs/server_startup.log",
  "exit_code": 1
}
EOF
    exit 1
fi
