# 智能通知过滤配置说明

## 功能概述

智能通知过滤系统可以根据事件类型和工具名称，自动过滤不重要的通知，只向Telegram发送关键信息。

## 配置文件：config.json

```json
"notification": {
  "level": "normal",
  "always_notify_events": ["stop", "error", "permission", "question"],
  "silent_tools": ["Read", "Grep", "Glob", "Edit", "Write", "Bash", "Task"],
  "silent_events": ["subagent", "tool_use"]
}
```

## 配置项说明

### 1. level（通知级别）

- **normal**（默认）：发送重要事件，过滤静默事件和静默工具
- **minimal**：仅发送 always_notify_events 中的事件
- **all**：发送所有通知（未来扩展）

### 2. always_notify_events（总是通知的事件）

这些事件**总是**会发送到Telegram，无论其他设置如何：

- **stop**：任务完成通知 ✅
- **error**：错误通知 ✅
- **permission**：权限请求 ✅
- **question**：问题询问 ✅

### 3. silent_events（静默事件列表）

这些事件**不会**发送通知到Telegram：

- **subagent**：子代理完成事件（太频繁）
- **tool_use**：工具执行事件（太频繁）

### 4. silent_tools（静默工具列表）

当 tool_use 事件不在 silent_events 中时，这些工具的执行**不会**发送通知：

- **Read**：读取文件
- **Grep**：搜索内容
- **Glob**：文件匹配
- **Edit**：编辑文件
- **Write**：写入文件
- **Bash**：执行命令
- **Task**：启动子任务

## 通知行为矩阵

| 事件类型 | 当前配置 | 说明 |
|---------|---------|------|
| Stop | ✅ 发送 | 任务完成，总是通知 |
| Error | ✅ 发送 | 错误，总是通知 |
| Permission | ✅ 发送 | 权限请求，总是通知 |
| Question | ✅ 发送 | 问题询问，总是通知 |
| Subagent | ❌ 静默 | 在 silent_events 中 |
| Tool Use | ❌ 静默 | 在 silent_events 中 |

## 使用场景

### 场景1：只接收任务完成通知（推荐，当前配置）

**配置**：
```json
"notification": {
  "level": "normal",
  "always_notify_events": ["stop", "error", "permission", "question"],
  "silent_tools": ["Read", "Grep", "Glob", "Edit", "Write", "Bash", "Task"],
  "silent_events": ["subagent", "tool_use"]
}
```

**效果**：
- ✅ 任务完成时收到通知
- ✅ 出错时收到通知
- ✅ 需要权限或回答问题时收到通知
- ❌ 子代理完成不通知（太频繁）
- ❌ 所有工具执行不通知（太频繁）

### 场景2：接收子代理完成通知

**配置**：
```json
"notification": {
  "level": "normal",
  "always_notify_events": ["stop", "error", "permission", "question"],
  "silent_tools": ["Read", "Grep", "Glob", "Edit", "Write", "Bash", "Task"],
  "silent_events": ["tool_use"]
}
```

**效果**：
- ✅ 任务完成时收到通知
- ✅ 子代理完成时收到通知
- ❌ 常规工具执行不通知

### 场景3：接收重要工具通知

**配置**：
```json
"notification": {
  "level": "normal",
  "always_notify_events": ["stop", "error", "permission", "question"],
  "silent_tools": ["Read", "Grep", "Glob", "Edit", "Write", "Bash", "Task"],
  "silent_events": ["subagent"]
}
```

**效果**：
- ✅ 任务完成时收到通知
- ✅ 重要工具（WebFetch等）执行时收到通知
- ❌ 常规工具（Read、Bash等）不通知
- ❌ 子代理完成不通知

### 场景4：极简模式（只要结果）

**配置**：
```json
"notification": {
  "level": "minimal",
  "always_notify_events": ["stop", "error"],
  "silent_tools": [],
  "silent_events": []
}
```

**效果**：
- ✅ 只在任务完成或出错时通知
- ❌ 所有中间过程都不通知

## 日志查看

查看过滤日志：
```bash
tail -f logs/webhook.log | grep -E "(Silencing|Notification)"
```

输出示例：
```
2025-12-26 20:48:49,360 [INFO] Silencing tool: Read
2025-12-26 20:48:49,360 [INFO] ✗ Notification silenced for event: tool_use
2025-12-26 20:48:52,059 [INFO] ✓ Notification sent for event: subagent
```

## 测试过滤功能

运行测试脚本：
```bash
./tests/test_filter.sh
```

该脚本会发送5个测试事件，验证过滤是否正常工作。

## 修改配置后

修改 `config.json` 后需要重启服务器：
```bash
pkill -f webhook_server.py
python3 webhook_server.py
```

或使用快捷命令：
```bash
/tel-start
```
