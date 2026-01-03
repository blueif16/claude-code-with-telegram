#!/bin/bash
# 配置验证脚本
# 返回: 0=成功, 1=失败
# 输出: JSON 格式的验证结果

set -e

# 查找配置文件（优先本地，其次全局）
find_config() {
    if [ -f ".claude-telegram/config.json" ]; then
        echo ".claude-telegram/config.json"
    elif [ -f "$HOME/.claude-telegram/config.json" ]; then
        echo "$HOME/.claude-telegram/config.json"
    else
        echo ""
    fi
}

CONFIG_FILE=$(find_config)
EXIT_CODE=0
MISSING_FIELDS=()
VALID_FIELDS=()
WARNINGS=()

# 检查配置文件是否存在
if [ -z "$CONFIG_FILE" ]; then
    cat <<EOF
{
  "success": false,
  "error": "配置文件未找到",
  "suggestion": "创建 .claude-telegram/config.json 或 ~/.claude-telegram/config.json",
  "exit_code": 1
}
EOF
    exit 1
fi

# 验证 JSON 格式
if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
    cat <<EOF
{
  "success": false,
  "error": "config.json 格式无效",
  "suggestion": "检查 JSON 语法",
  "exit_code": 1
}
EOF
    exit 1
fi

# 检查必需字段
check_field() {
    local field=$1
    local value=$(jq -r "$field" "$CONFIG_FILE" 2>/dev/null)

    if [ "$value" = "null" ] || [ -z "$value" ]; then
        MISSING_FIELDS+=("$field")
        EXIT_CODE=1
    else
        VALID_FIELDS+=("$field")

        # 检查是否是默认值（需要修改）
        if [[ "$value" == *"YOUR_"* ]] || [[ "$value" == *"CHANGE_ME"* ]]; then
            WARNINGS+=("$field 包含默认值，需要修改")
        fi
    fi
}

# 验证所有必需字段
check_field ".telegram.bot_token"
check_field ".telegram.chat_id"
check_field ".telegram.secret_token"
check_field ".webhook.host"
check_field ".webhook.port"

# session_name 是可选的（可以从 git 或目录名自动获取）
# check_field ".claude.session_name"

# 输出结果
cat <<EOF
{
  "success": $([ $EXIT_CODE -eq 0 ] && echo "true" || echo "false"),
  "valid_fields": [$(printf '"%s",' "${VALID_FIELDS[@]}" | sed 's/,$//')],
  "missing_fields": [$(printf '"%s",' "${MISSING_FIELDS[@]}" | sed 's/,$//')],
  "warnings": [$(printf '"%s",' "${WARNINGS[@]}" | sed 's/,$//')],
  "exit_code": $EXIT_CODE
}
EOF

exit $EXIT_CODE
