# P0 - 智能过滤（立即实施）

## 目标

实现智能通知过滤系统，将通知数量减少80%，只在关键时刻通知用户。

## 核心问题

当前系统每个工具调用都发送通知，造成信息过载。需要实现智能过滤，静默执行常规操作，只通知关键事件。

## 范围

### 1. 添加通知级别配置
- 在 config.json 中添加 notification_level 配置项
- 支持三个级别：minimal、normal、verbose
- 默认为 normal

### 2. 实现过滤逻辑
修改 notify-telegram-smart.sh：
- 添加 should_notify() 函数判断是否发送通知
- minimal: 只通知完成和错误
- normal: 通知完成、错误、需要决策（默认）
- verbose: 通知所有工具调用（当前行为）

### 3. 修改 webhook 服务器
修改 webhook_server.py：
- 添加历史记录存储（内存中的列表）
- 所有事件都记录到历史，但只有符合过滤条件的才发送通知
- 添加 tool_history 全局变量

### 4. 实现通知策略

**必须通知（高优先级）**：
- Stop hook: 任务完成
- Error: 执行失败
- Permission: 需要权限批准
- Question: 需要用户选择

**静默执行（不通知）**：
- Read/Grep/Glob: 文件读取和搜索
- Edit/Write: 代码修改（除非失败）
- Bash: 常规命令（除非失败）
- Task: 子任务启动

## 验收标准

- [ ] config.json 包含 notification_level 配置
- [ ] notify-telegram-smart.sh 实现 should_notify() 函数
- [ ] webhook_server.py 添加 tool_history 存储
- [ ] minimal 模式下只收到完成和错误通知
- [ ] normal 模式下收到完成、错误、决策通知
- [ ] verbose 模式下收到所有通知（保持当前行为）
- [ ] 所有事件都记录到历史，无论是否通知
- [ ] 通知数量相比当前减少约80%（在normal模式下）

## 上下文边界

**拥有:**
- .claude/notify-telegram-smart.sh（添加过滤逻辑）
- webhook_server.py（添加历史存储和过滤）
- config.json（添加配置项）

**读取:**
- .claude/settings.json（hook配置）

**禁止:**
- tests/*（测试文件由后续任务处理）
- README.md（文档更新由后续任务处理）

## 实现细节

### config.json 新增配置
```json
{
  "notification": {
    "level": "normal",
    "always_notify_events": ["stop", "error", "permission", "question"],
    "silent_tools": ["Read", "Grep", "Glob", "Edit", "Write", "Bash", "Task"]
  }
}
```

### should_notify() 逻辑
```bash
should_notify() {
    local event_type=$1
    local tool_name=$2
    local level=$(jq -r '.notification.level // "normal"' config.json)

    case $level in
        "minimal")
            [[ "$event_type" == "stop" || "$event_type" == "error" ]]
            ;;
        "normal")
            # 总是通知的事件
            if [[ "$event_type" == "stop" || "$event_type" == "error" ||
                  "$event_type" == "permission" || "$event_type" == "question" ]]; then
                return 0
            fi
            # 工具调用：只通知非静默工具
            if [[ "$event_type" == "tool_use" ]]; then
                ! is_silent_tool "$tool_name"
            else
                return 1
            fi
            ;;
        "verbose")
            return 0
            ;;
    esac
}
```

## 测试计划

1. 设置 notification_level 为 minimal，执行任务，验证只收到完成通知
2. 设置为 normal，验证收到完成和决策通知，但不收到 Read/Edit 通知
3. 设置为 verbose，验证收到所有通知
4. 验证历史记录包含所有事件（包括未通知的）
