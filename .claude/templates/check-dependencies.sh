#!/bin/bash
# 前置依赖检查脚本
# 返回: 0=成功, 1=失败
# 输出: JSON 格式的检查结果

set -e

# 初始化结果
MISSING_DEPS=()
INSTALLED_DEPS=()
EXIT_CODE=0

# 检查 tmux
if command -v tmux &> /dev/null; then
    TMUX_VERSION=$(tmux -V)
    INSTALLED_DEPS+=("tmux:$TMUX_VERSION")
else
    MISSING_DEPS+=("tmux")
    EXIT_CODE=1
fi

# 检查 jq
if command -v jq &> /dev/null; then
    JQ_VERSION=$(jq --version)
    INSTALLED_DEPS+=("jq:$JQ_VERSION")
else
    MISSING_DEPS+=("jq")
    EXIT_CODE=1
fi

# 检查 Python3
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    INSTALLED_DEPS+=("python3:$PYTHON_VERSION")
else
    MISSING_DEPS+=("python3")
    EXIT_CODE=1
fi

# 检查 pip3
if command -v pip3 &> /dev/null; then
    INSTALLED_DEPS+=("pip3:installed")
else
    MISSING_DEPS+=("pip3")
    EXIT_CODE=1
fi

# 检查 curl
if command -v curl &> /dev/null; then
    INSTALLED_DEPS+=("curl:installed")
else
    MISSING_DEPS+=("curl")
    EXIT_CODE=1
fi

# 检查 Python 依赖
if [ -f "requirements.txt" ]; then
    if python3 -c "import flask; import requests" &> /dev/null; then
        INSTALLED_DEPS+=("python-deps:installed")
    else
        MISSING_DEPS+=("python-deps")
        EXIT_CODE=1
    fi
else
    MISSING_DEPS+=("requirements.txt")
    EXIT_CODE=1
fi

# 输出 JSON 结果
cat <<EOF
{
  "success": $([ $EXIT_CODE -eq 0 ] && echo "true" || echo "false"),
  "installed": [$(printf '"%s",' "${INSTALLED_DEPS[@]}" | sed 's/,$//')],
  "missing": [$(printf '"%s",' "${MISSING_DEPS[@]}" | sed 's/,$//')],
  "exit_code": $EXIT_CODE
}
EOF

exit $EXIT_CODE
