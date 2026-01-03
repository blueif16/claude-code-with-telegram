#!/bin/bash
# tel-start - Telegram Webhook Server Launcher
# 全局启动命令，支持主服务器和项目服务器模式

set -e

# 确保 tmux 在 PATH 中
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本根目录（tel-start 项目位置）
SCRIPT_ROOT="/Users/tk/Desktop/claude-code-with-telegram"

# 配置文件路径
LOCAL_CONFIG=".claude-telegram/config.json"
GLOBAL_CONFIG="$HOME/.claude-telegram/config.json"

# 日志函数
log_info() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_step() {
    echo -e "${BLUE}🔹${NC} $1"
}

# 1. 检查依赖
check_dependencies() {
    log_step "检查依赖..."

    if ! "$SCRIPT_ROOT/.claude/templates/check-dependencies.sh" 2>&1; then
        log_error "依赖检查失败"
        exit 1
    fi
}

# 2. 查找配置文件
find_config() {
    if [ -f "$LOCAL_CONFIG" ]; then
        echo "$LOCAL_CONFIG"
    elif [ -f "$GLOBAL_CONFIG" ]; then
        echo "$GLOBAL_CONFIG"
    else
        log_error "配置文件未找到"
        echo "请创建以下任一配置文件:"
        echo "  • .claude-telegram/config.json (项目配置)"
        echo "  • ~/.claude-telegram/config.json (主配置)"
        exit 1
    fi
}

# 3. 确定 session 名称
get_session_name() {
    local config_file=$1

    # 只有当前目录有本地配置时才从配置读取
    if [ -f "$LOCAL_CONFIG" ]; then
        local session_name=$(jq -r '.claude.session_name // empty' "$config_file" 2>/dev/null)
        if [ -n "$session_name" ] && [ "$session_name" != "null" ]; then
            echo "$session_name"
            return
        fi
    fi

    # 检查是否为 git 仓库
    if git rev-parse --git-dir > /dev/null 2>&1; then
        local repo_name=$(basename "$(git rev-parse --show-toplevel)")
        echo "$repo_name"
        return
    fi

    # 使用当前目录名
    echo "$(basename "$(pwd)")"
}

# 4. 获取端口号
get_port() {
    local config_file=$1
    local session_name=$2

    # 如果是主服务器，使用固定端口 8000
    if [ "$session_name" = "main" ]; then
        echo "8000"
        return
    fi

    # 项目服务器，从配置读取
    local port=$(jq -r '.webhook.port // empty' "$config_file" 2>/dev/null)
    # 如果端口有效且不是 8000，使用它
    if [ -n "$port" ] && [ "$port" != "null" ] && [ "$port" != "8000" ]; then
        echo "$port"
        return
    fi

    # 自动分配端口（从 8100 开始）
    local start_port=$(jq -r '.webhook.port_range_start // 8100' "$GLOBAL_CONFIG" 2>/dev/null)
    local next_port=$start_port

    # 查找可用端口
    while lsof -i ":$next_port" > /dev/null 2>&1; do
        ((next_port++))
    done

    echo "$next_port"
}

# 5. 创建项目配置文件
create_project_config() {
    local session_name=$1
    local port=$2

    log_step "创建项目配置文件..."

    mkdir -p .claude-telegram

    cat > .claude-telegram/config.json <<EOF
{
  "telegram": {
    "bot_token": "$(jq -r '.telegram.bot_token' "$GLOBAL_CONFIG")",
    "chat_id": "$(jq -r '.telegram.chat_id' "$GLOBAL_CONFIG")",
    "secret_token": "$(jq -r '.telegram.secret_token' "$GLOBAL_CONFIG")"
  },
  "webhook": {
    "host": "127.0.0.1",
    "port": $port
  },
  "claude": {
    "session_name": "$session_name"
  }
}
EOF

    log_info "已创建配置文件: .claude-telegram/config.json"
}

# 5. 检查/创建 tmux session
ensure_tmux_session() {
    local session_name=$1

    # 使用 list-sessions 检查是否存在
    if tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -q "^${session_name}$"; then
        log_info "Session '$session_name' 已存在"
        # 发送 Ctrl+C 停止当前进程
        tmux send-keys -t "$session_name" C-c 2>/dev/null || true
        sleep 1
    else
        log_step "创建 tmux session: $session_name"
        tmux new-session -d -s "$session_name"
        log_info "Session '$session_name' 已创建"
    fi
}

# 6. 启动服务器（先杀掉旧进程）
start_server() {
    local session_name=$1
    local port=$2
    local config_file=$3
    local work_dir=$(pwd)

    log_step "在 session '$session_name' 中启动服务器..."

    # 如果端口被占用，先杀掉进程
    if lsof -i ":$port" > /dev/null 2>&1; then
        PID=$(lsof -ti ":$port")
        log_step "终止占用端口 $port 的进程 (PID: $PID)"
        kill -9 "$PID" 2>/dev/null || true
        sleep 2
    fi

    # 确保 logs 目录存在并设置日志路径
    local log_dir
    local log_file
    if [ "$session_name" = "main" ]; then
        log_dir="$HOME/.claude-telegram/logs"
    else
        log_dir="$work_dir/logs"
    fi

    # 创建 logs 目录（如果不存在）
    if [ ! -d "$log_dir" ]; then
        mkdir -p "$log_dir" 2>/dev/null || {
            log_error "无法创建日志目录: $log_dir"
            exit 1
        }
    fi

    # 检查目录权限，如果不可写则使用带时间戳的子目录
    if [ ! -w "$log_dir" ]; then
        log_warn "日志目录不可写，使用临时目录..."
        log_dir="$log_dir.$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$log_dir"
    fi

    log_file="$log_dir/webhook.log"

    # 如果日志文件存在但不可写，使用新文件名
    if [ -f "$log_file" ] && [ ! -w "$log_file" ]; then
        log_warn "日志文件不可写，使用新文件名..."
        log_file="$log_dir/webhook.$(date +%Y%m%d_%H%M%S).log"
    fi

    # 切换到工作目录
    tmux send-keys -t "$session_name" "cd '$work_dir'" C-m

    # 设置环境变量并启动服务器（带日志重定向）
    tmux send-keys -t "$session_name" "export TEL_CONFIG='$config_file'" C-m
    tmux send-keys -t "$session_name" "export TEL_PORT='$port'" C-m
    tmux send-keys -t "$session_name" "python3 '$SCRIPT_ROOT/webhook_server.py' >> '$log_file' 2>&1" C-m

    log_info "日志文件: $log_file"

    # 等待服务器启动
    sleep 2
}

# 7. 健康检查
health_check() {
    local port=$1
    local host="127.0.0.1"

    log_step "执行健康检查..."

    for i in {1..5}; do
        if curl -s "http://$host:$port/health" > /dev/null 2>&1; then
            log_info "服务器健康检查通过"
            return 0
        fi
        sleep 1
    done

    log_error "服务器健康检查失败"
    return 1
}

# 8. 显示启动信息
show_info() {
    local session_name=$1
    local port=$2
    local config_file=$3
    local work_dir=$(pwd)

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📡 Webhook 服务器已启动"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "🔹 Session: $session_name"
    if [ "$session_name" != "main" ]; then
        echo "🔹 项目路径: $work_dir"
    fi
    echo "🌐 服务地址: http://127.0.0.1:$port"
    echo "📊 健康检查: http://127.0.0.1:$port/health"
    echo "📝 配置文件: $config_file"
    echo ""
    echo "可用端点:"
    echo "  • /claude-hook - 接收 Claude Code 通知"
    echo "  • /telegram-webhook - 接收 Telegram 命令"
    echo "  • /health - 健康检查"
    echo ""
    echo "查看 session: tmux attach -t $session_name"
    echo ""
}

# 检查并启动 cloudflared tunnel
ensure_cloudflared_tunnel() {
    log_step "检查 cloudflared tunnel 状态..."

    # 检查 cloudflared 是否已运行
    if ps aux | grep -v grep | grep "cloudflared tunnel run" > /dev/null 2>&1; then
        log_info "Cloudflared tunnel 已在运行"
        return 0
    fi

    # 查找 cloudflared 可执行文件
    local cloudflared_bin=""
    for path in /opt/homebrew/bin/cloudflared /usr/local/bin/cloudflared ~/bin/cloudflared; do
        if [ -x "$path" ]; then
            cloudflared_bin="$path"
            break
        fi
    done

    if [ -z "$cloudflared_bin" ]; then
        log_warn "未找到 cloudflared，跳过 tunnel 启动"
        log_warn "如需 Telegram 远程访问，请安装 cloudflared"
        return 0
    fi

    # 从配置读取 tunnel 名称（如果有）
    local tunnel_name=$(jq -r '.cloudflared.tunnel_name // "claude-bot"' "$GLOBAL_CONFIG" 2>/dev/null)

    log_step "启动 cloudflared tunnel: $tunnel_name"

    # 启动 tunnel（后台运行）
    local tunnel_log="$HOME/.claude-telegram/logs/cloudflared.log"
    mkdir -p "$(dirname "$tunnel_log")"
    nohup "$cloudflared_bin" tunnel run "$tunnel_name" >> "$tunnel_log" 2>&1 &

    log_info "Cloudflared tunnel 已启动"
    log_info "日志文件: $tunnel_log"

    # 等待 tunnel 建立连接
    sleep 3
}

# 检查并启动主服务器（总是重启）
ensure_main_server() {
    log_step "检查主服务器状态..."

    # 确保主配置存在
    if [ ! -f "$GLOBAL_CONFIG" ]; then
        log_error "主配置文件不存在: $GLOBAL_CONFIG"
        exit 1
    fi

    # 先启动 cloudflared tunnel（如果需要）
    ensure_cloudflared_tunnel

    # 检查 main session 是否存在
    if tmux has-session -t main 2>/dev/null; then
        log_warn "main session 已存在，重启服务器..."

        # 杀掉 session 中的进程（发送 Ctrl+C）
        tmux send-keys -t main C-c 2>/dev/null || true
        sleep 1
    else
        log_step "创建 main session..."
        tmux new-session -d -s main
    fi

    # 如果端口还被占用，强制杀掉进程
    if lsof -i :8000 > /dev/null 2>&1; then
        PID=$(lsof -ti :8000)
        log_step "终止占用端口 8000 的进程 (PID: $PID)"
        kill -9 "$PID" 2>/dev/null || true
        sleep 2
    fi

    log_step "启动主服务器..."

    # 确保 logs 目录存在
    mkdir -p "$HOME/.claude-telegram/logs"
    local log_file="$HOME/.claude-telegram/logs/webhook.log"

    # 在 main session 中启动服务器
    tmux send-keys -t main "cd ~" C-m
    tmux send-keys -t main "export TEL_CONFIG='$GLOBAL_CONFIG'" C-m
    tmux send-keys -t main "export TEL_PORT='8000'" C-m
    tmux send-keys -t main "python3 '$SCRIPT_ROOT/webhook_server.py' >> '$log_file' 2>&1" C-m

    log_info "主服务器日志: $log_file"

    # 等待启动（增加等待时间）
    sleep 3

    # 健康检查（增加重试次数和间隔）
    for i in {1..10}; do
        if curl -s "http://127.0.0.1:8000/health" > /dev/null 2>&1; then
            log_info "主服务器启动成功 (session: main, port: 8000)"
            return 0
        fi
        sleep 1
    done

    log_error "主服务器启动失败"
    log_error "请检查日志: $log_file"
    return 1
}

# 记录 session 到历史
record_session() {
    local session_name=$1
    local project_path=$2
    local port=$3

    local history_file="$HOME/.claude-telegram/sessions.json"

    # 确保目录存在
    mkdir -p "$HOME/.claude-telegram"

    # 初始化历史文件
    if [ ! -f "$history_file" ]; then
        echo '{"sessions": []}' > "$history_file"
    fi

    # 添加或更新 session 记录
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    jq --arg name "$session_name" \
       --arg path "$project_path" \
       --arg port "$port" \
       --arg time "$timestamp" \
       '.sessions = ([.sessions[] | select(.name != $name)] + [{
           "name": $name,
           "path": $path,
           "port": $port,
           "last_used": $time
       }] | sort_by(.last_used) | reverse | .[0:10])' \
       "$history_file" > "$history_file.tmp" && mv "$history_file.tmp" "$history_file"
}

# 主函数
main() {
    echo ""
    echo "🚀 启动 Telegram Webhook 服务器"
    echo ""

    # 0. 检查依赖
    check_dependencies

    # 1. 确保主服务器运行
    ensure_main_server || exit 1

    echo ""
    log_step "启动项目服务器..."
    echo ""

    # 2. 查找配置文件
    CONFIG_FILE=$(find_config)
    log_info "使用配置: $CONFIG_FILE"

    # 3. 确定 session 名称
    SESSION_NAME=$(get_session_name "$CONFIG_FILE")
    log_info "Session 名称: $SESSION_NAME"

    # 4. 获取端口号（如果没有本地配置，先分配端口再创建配置）
    if [ ! -f "$LOCAL_CONFIG" ]; then
        # 自动分配端口
        local start_port=$(jq -r '.webhook.port_range_start // 8100' "$GLOBAL_CONFIG" 2>/dev/null)
        PORT=$start_port
        while lsof -i ":$PORT" > /dev/null 2>&1; do
            ((PORT++))
        done
        log_info "分配端口: $PORT"

        # 创建配置文件
        create_project_config "$SESSION_NAME" "$PORT"
        CONFIG_FILE="$LOCAL_CONFIG"
    else
        # 从配置读取端口
        PORT=$(get_port "$CONFIG_FILE" "$SESSION_NAME")
        log_info "使用端口: $PORT"
    fi

    # 5. 端口占用检查已移到 start_server 函数中处理

    # 6. 确保 tmux session 存在
    ensure_tmux_session "$SESSION_NAME"

    # 7. 启动服务器
    start_server "$SESSION_NAME" "$PORT" "$CONFIG_FILE"

    # 8. 健康检查
    if health_check "$PORT"; then
        # 记录 session 到历史
        record_session "$SESSION_NAME" "$(pwd)" "$PORT"

        show_info "$SESSION_NAME" "$PORT" "$CONFIG_FILE"
    else
        log_error "服务器启动失败，请检查日志"
        exit 1
    fi
}

# 执行主函数
main "$@"

