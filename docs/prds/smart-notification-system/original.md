# Smart Notification System PRD

## 目标

构建智能通知系统，让程序员能高效监控多个Claude Code项目，减少噪音，专注关键事件。

## 核心问题

**当前系统**：每个工具调用都发送通知 → 信息过载，无法专注工作

**理想状态**：静默执行，只在关键时刻通知 → 高效监控，按需查询

## 使用场景

### 场景1：日常开发（最常见）
```
用户在Telegram发送: /ask 重构webhook_server.py的错误处理

系统行为:
- ✅ 确认任务已接收
- 🔇 静默执行（读文件、分析代码、编辑文件）
- ✅ 完成时通知结果摘要

用户体验: 发送任务 → 继续工作 → 收到完成通知
```

### 场景2：需要决策
```
Claude Code遇到需要用户选择的情况

系统行为:
- 🔔 立即通知
- 📋 展示选项
- ⏸️ 等待用户响应

用户体验: 收到通知 → 做出选择 → 继续执行
```

### 场景3：查询历史（按需）
```
用户想了解某个工具的执行情况

用户发送: /history bash
或: /last 5

系统行为:
- 📜 返回最近的bash工具调用记录
- 包含输入、输出、时间戳

用户体验: 主动查询 → 获取详细信息
```

## 通知策略

### 🔔 必须通知（高优先级）

| 事件 | 触发条件 | 通知内容 |
|------|---------|---------|
| 任务完成 | Stop hook | 结果摘要 + 耗时 |
| 需要权限 | 工具需要批准 | 工具名称 + 操作说明 |
| 需要选择 | AskUserQuestion | 问题 + 选项 |
| 错误发生 | 执行失败 | 错误类型 + 简要说明 |
| 长时间运行 | 超过5分钟 | 进度更新 |

### 🔇 静默执行（不通知）

- Read/Grep/Glob（文件读取和搜索）
- Edit/Write（代码修改，除非失败）
- Bash（常规命令，除非失败）
- Task（子任务启动）

### 📊 可选通知（用户配置）

用户可在config.json配置通知级别：
- `minimal`: 只通知完成和错误
- `normal`: 通知完成、错误、需要决策（默认）
- `verbose`: 通知所有工具调用（当前行为）

## 技术实现

### 阶段1：智能过滤（单项目）

**修改notify-telegram-smart.sh**：
```bash
# 添加通知级别判断
NOTIFICATION_LEVEL=${NOTIFICATION_LEVEL:-"normal"}

should_notify() {
    local event_type=$1
    local tool_name=$2

    case $NOTIFICATION_LEVEL in
        "minimal")
            [[ "$event_type" == "stop" || "$event_type" == "error" ]]
            ;;
        "normal")
            [[ "$event_type" == "stop" ||
               "$event_type" == "error" ||
               "$event_type" == "permission" ||
               "$event_type" == "question" ]]
            ;;
        "verbose")
            return 0
            ;;
    esac
}
```

**修改webhook_server.py**：
```python
# 添加历史记录存储
tool_history = []

@app.route('/claude-hook', methods=['POST'])
def claude_hook():
    data = request.get_json()
    event = data.get('event')

    # 始终记录到历史
    tool_history.append({
        'timestamp': datetime.now().isoformat(),
        'event': event,
        'data': data
    })

    # 根据策略决定是否通知
    if should_notify(event, data):
        send_telegram_message(format_message(data))

    return jsonify({'ok': True}), 200

@app.route('/history', methods=['POST'])
def get_history():
    # 处理 /history 命令
    filters = parse_history_query(request.get_json())
    results = filter_history(tool_history, filters)
    send_telegram_message(format_history(results))
    return jsonify({'ok': True}), 200
```

### 阶段2：多项目支持

**配置结构**：
```json
{
  "projects": {
    "project-a": {
      "path": "/path/to/project-a",
      "tmux_session": "claude-a",
      "notification_level": "normal"
    },
    "project-b": {
      "path": "/path/to/project-b",
      "tmux_session": "claude-b",
      "notification_level": "minimal"
    }
  },
  "active_project": "project-a"
}
```

**新增命令**：
```
/switch project-b    - 切换活跃项目
/projects            - 列出所有项目状态
/ask@project-b <任务> - 向特定项目发送任务
```

## 新增Telegram命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `/history [filter]` | 查询工具调用历史 | `/history bash` |
| `/last [n]` | 查看最近n条记录 | `/last 5` |
| `/level <minimal\|normal\|verbose>` | 设置通知级别 | `/level minimal` |
| `/projects` | 列出所有项目 | `/projects` |
| `/switch <project>` | 切换项目 | `/switch project-b` |

## 实施计划

### P0 - 智能过滤（立即实施）
1. 添加通知级别配置
2. 实现should_notify逻辑
3. 修改hook脚本应用过滤
4. 添加历史记录存储

### P1 - 历史查询（1周内）
1. 实现/history命令
2. 实现/last命令
3. 添加历史记录持久化
4. 实现过滤和搜索

### P2 - 多项目支持（2周内）
1. 设计多项目配置结构
2. 实现项目切换逻辑
3. 添加项目状态监控
4. 实现@project语法

## 成功指标

- 通知数量减少80%（从每个工具调用 → 只通知关键事件）
- 用户主动查询历史 < 5次/天
- 多项目切换延迟 < 2秒
- 历史查询响应 < 1秒

## 最有效的使用方式

**程序员的理想工作流**：
1. 早上启动：`/projects` 查看所有项目状态
2. 发送任务：`/ask@backend 优化数据库查询`
3. 继续工作：专注当前任务，不被打断
4. 收到通知：任务完成或需要决策时
5. 按需查询：`/history` 查看执行细节
6. 切换项目：`/switch frontend` 处理另一个项目

**核心价值**：让Claude Code成为后台助手，而不是噪音制造者
