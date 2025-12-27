#!/bin/bash
# 配置验证脚本
# 返回: 0=成功, 1=失败
# 输出: JSON 格式的验证结果

set -e

CONFIG_FILE="config.json"
EXIT_CODE=0
MISSING_FIELDS=()
VALID_FIELDS=()
WARNINGS=()

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    cat <<EOF
{
  "success": false,
  "error": "config.json 不存在",
  "suggestion": "运行 ./setup.sh 或从 config.json.example 复制",
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
check_field ".claude.tmux_session"

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
