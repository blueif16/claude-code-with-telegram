#!/bin/bash

# Setup script for Claude Code + Telegram integration
# Supports macOS and WSL/Linux

set -e

echo "=========================================="
echo "Claude Code + Telegram 设置向导"
echo "=========================================="
echo ""

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "项目目录: $PROJECT_ROOT"
echo ""

# Step 1: Check dependencies
echo "步骤 1/4: 检查依赖..."
if [ -f "$PROJECT_ROOT/check_dependencies.sh" ]; then
    bash "$PROJECT_ROOT/check_dependencies.sh"
else
    echo "⚠️  check_dependencies.sh 未找到，跳过依赖检查"
fi
echo ""

# Step 2: Generate settings.json with correct paths
echo "步骤 2/4: 生成 .claude/settings.json..."
if [ -f "$PROJECT_ROOT/.claude/settings.json.template" ]; then
    sed "s|{{PROJECT_ROOT}}|$PROJECT_ROOT|g" \
        "$PROJECT_ROOT/.claude/settings.json.template" > \
        "$PROJECT_ROOT/.claude/settings.json"
    echo "✅ settings.json 已生成"
else
    echo "⚠️  settings.json.template 未找到"
fi
echo ""

# Step 3: Setup config.json
echo "步骤 3/4: 配置 config.json..."
if [ ! -f "$PROJECT_ROOT/config.json" ]; then
    if [ -f "$PROJECT_ROOT/config.json.example" ]; then
        cp "$PROJECT_ROOT/config.json.example" "$PROJECT_ROOT/config.json"
        echo "✅ 已从 config.json.example 创建 config.json"
        echo ""
        echo "⚠️  请编辑 config.json 并填入你的 Telegram 凭证:"
        echo "   - bot_token: 从 @BotFather 获取"
        echo "   - chat_id: 从 Telegram API 获取"
        echo "   - secret_token: 运行 'openssl rand -hex 32' 生成"
    else
        echo "❌ config.json.example 未找到"
    fi
else
    echo "✅ config.json 已存在"
fi
echo ""

# Step 4: Set permissions
echo "步骤 4/4: 设置权限..."
chmod +x "$PROJECT_ROOT/.claude/notify-telegram-smart.sh"
chmod +x "$PROJECT_ROOT/check_dependencies.sh"
chmod +x "$PROJECT_ROOT/tests"/*.sh 2>/dev/null || true
echo "✅ 权限设置完成"
echo ""

# Create logs directory
mkdir -p "$PROJECT_ROOT/logs"

echo "=========================================="
echo "✅ 设置完成！"
echo "=========================================="
echo ""
echo "下一步:"
echo "1. 编辑 config.json 填入 Telegram 凭证"
echo "2. 启动 webhook 服务器:"
echo "   python3 webhook_server.py"
echo ""
echo "3. 测试系统:"
echo "   ./tests/test_local_only.sh"
echo ""
echo "4. (可选) 如果要在其他机器使用，重新运行:"
echo "   ./setup.sh"
