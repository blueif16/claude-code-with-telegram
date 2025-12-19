#!/bin/bash

# Dependency checker and installer for Claude Code + Telegram system
# Supports macOS and WSL/Linux

set -e

echo "=========================================="
echo "检查系统依赖"
echo "=========================================="
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    echo "检测到系统: macOS"
elif [[ -f /proc/version ]] && grep -qi microsoft /proc/version; then
    OS="wsl"
    echo "检测到系统: WSL"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    echo "检测到系统: Linux"
else
    echo "❌ 不支持的操作系统: $OSTYPE"
    exit 1
fi
echo ""

# Check and install tmux
echo "1. 检查 tmux..."
if command -v tmux &> /dev/null; then
    TMUX_VERSION=$(tmux -V)
    echo "✅ tmux 已安装: $TMUX_VERSION"
else
    echo "❌ tmux 未安装，正在安装..."
    if [[ "$OS" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install tmux
        else
            echo "❌ 需要 Homebrew 来安装 tmux"
            echo "请访问: https://brew.sh"
            exit 1
        fi
    elif [[ "$OS" == "wsl" ]] || [[ "$OS" == "linux" ]]; then
        sudo apt-get update && sudo apt-get install -y tmux
    fi
    echo "✅ tmux 安装完成"
fi
echo ""

# Check Python3
echo "2. 检查 Python3..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ Python3 已安装: $PYTHON_VERSION"
else
    echo "❌ Python3 未安装"
    exit 1
fi
echo ""

# Check pip3
echo "3. 检查 pip3..."
if command -v pip3 &> /dev/null; then
    echo "✅ pip3 已安装"
else
    echo "❌ pip3 未安装，正在安装..."
    if [[ "$OS" == "macos" ]]; then
        python3 -m ensurepip --upgrade
    else
        sudo apt-get install -y python3-pip
    fi
fi
echo ""

# Check jq
echo "4. 检查 jq..."
if command -v jq &> /dev/null; then
    JQ_VERSION=$(jq --version)
    echo "✅ jq 已安装: $JQ_VERSION"
else
    echo "❌ jq 未安装，正在安装..."
    if [[ "$OS" == "macos" ]]; then
        brew install jq
    else
        sudo apt-get install -y jq
    fi
    echo "✅ jq 安装完成"
fi
echo ""

# Check Python dependencies
echo "5. 检查 Python 依赖..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --quiet
    echo "✅ Python 依赖已安装"
else
    echo "⚠️  requirements.txt 未找到"
fi
echo ""

# Check curl
echo "6. 检查 curl..."
if command -v curl &> /dev/null; then
    echo "✅ curl 已安装"
else
    echo "❌ curl 未安装"
    exit 1
fi
echo ""

echo "=========================================="
echo "✅ 所有依赖检查完成"
echo "=========================================="
