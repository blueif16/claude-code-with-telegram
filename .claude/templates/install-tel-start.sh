#!/bin/bash
# install-tel-start.sh - 安装 tel-start 全局命令

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_SCRIPT="$SCRIPT_DIR/tel-start.sh"
TARGET_PATH="/usr/local/bin/tel-start"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 安装 tel-start 全局命令"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查源文件是否存在
if [ ! -f "$SOURCE_SCRIPT" ]; then
    echo -e "${RED}❌${NC} 源文件不存在: $SOURCE_SCRIPT"
    exit 1
fi

# 检查是否已安装
NEED_REINSTALL=false
if [ -f "$TARGET_PATH" ]; then
    echo -e "${YELLOW}⚠️${NC}  tel-start 已安装: $TARGET_PATH"

    # 检查权限是否正确
    PERMS=$(stat -f "%Lp" "$TARGET_PATH" 2>/dev/null || stat -c "%a" "$TARGET_PATH" 2>/dev/null)
    if [ "$PERMS" != "755" ]; then
        echo -e "${YELLOW}⚠️${NC}  权限不正确 (当前: $PERMS, 需要: 755)"
        NEED_REINSTALL=true
    fi

    if [ "$NEED_REINSTALL" = false ]; then
        echo ""
        read -p "是否覆盖安装？[y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "安装取消"
            exit 0
        fi
    else
        echo -e "${BLUE}🔹${NC} 自动修复权限..."
    fi
fi

# 复制文件并设置权限（一次性完成）
echo -e "${BLUE}🔹${NC} 安装 tel-start 到 $TARGET_PATH"
sudo bash -c "cp '$SOURCE_SCRIPT' '$TARGET_PATH' && chmod 755 '$TARGET_PATH'"

# 验证安装
if command -v tel-start > /dev/null 2>&1; then
    echo ""
    echo -e "${GREEN}✅${NC} tel-start 安装成功！"
    echo ""
    echo "安装位置: $TARGET_PATH"
    echo ""
    echo "使用方法:"
    echo "  tel-start          # 在当前目录启动服务器"
    echo "  cd ~ && tel-start  # 启动主服务器"
    echo ""
    echo "返回 JSON 格式结果:"
    cat <<'EOF'
{
  "success": true,
  "installed_path": "/usr/local/bin/tel-start",
  "message": "tel-start 安装成功"
}
EOF
else
    echo -e "${RED}❌${NC} 安装失败，请检查权限"
    cat <<'EOF'
{
  "success": false,
  "error": "安装失败",
  "suggestion": "检查是否有 sudo 权限"
}
EOF
    exit 1
fi
