#!/bin/bash
# 前置依赖检查脚本 - 简化版，只检查库是否存在

# 检查 Python 库
python3 -c "import flask; import requests" 2>/dev/null || {
    echo "缺少 Python 库，正在安装..."
    pip3 install flask requests -q
}

echo "依赖检查通过"
exit 0
