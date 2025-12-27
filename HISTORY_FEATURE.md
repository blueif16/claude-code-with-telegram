# 历史记录功能 (P1)

## 功能概述

为webhook_server.py添加了持久化历史记录功能，支持查询和过滤Claude Code事件历史。

## 实现内容

### 1. 数据持久化
- **存储位置**: `logs/history.json`
- **数据结构**: JSON数组，每条记录包含：
  - `timestamp`: ISO格式时间戳
  - `event_type`: 事件类型 (stop/tool_use/subagent)
  - `message`: 格式化消息
  - `raw_data`: 原始事件数据
- **容量限制**: 最多保存100条记录（可配置）

### 2. 核心函数

#### `load_history()`
从JSON文件加载历史记录

#### `save_history(history)`
保存历史记录到JSON文件

#### `add_to_history(event_type, message, raw_data)`
添加新记录到历史，自动维护容量限制

#### `get_history(limit=10, event_type=None)`
获取历史记录，支持：
- `limit`: 返回最近N条记录
- `event_type`: 按事件类型过滤

### 3. Telegram命令

#### `/last`
显示最近一条记录（任意类型）
- 显示完整时间戳
- 显示事件类型
- 显示消息内容（最多800字符）

#### `/history [N] [type]`
显示历史记录列表
- 默认显示最近10条
- 支持指定数量：`/history 20`
- 支持类型过滤：`/history stop`
- 支持组合：`/history 15 tool_use`
- 最多显示50条

**示例**：
```
/history          # 最近10条
/history 20       # 最近20条
/history stop     # 所有stop类型
/history 15 tool_use  # 最近15条tool_use
```

### 4. 集成点

在 `/claude-hook` 端点中，每次接收到事件时：
1. 更新内存中的 `last_outputs`（保持原有功能）
2. 调用 `add_to_history()` 持久化保存
3. 发送Telegram通知

## 测试验证

✅ 历史记录持久化存储
✅ 记录加载和保存
✅ 容量限制（100条）
✅ `/last` 命令
✅ `/history` 命令（默认）
✅ `/history N` 命令（指定数量）
✅ `/history type` 命令（类型过滤）
✅ `/history N type` 命令（组合过滤）

## 文件变更

- `webhook_server.py`: 添加历史记录功能（约60行新代码）
- `logs/history.json`: 新增历史记录存储文件（自动创建）

## 兼容性

- 保持所有原有功能不变
- `/last_output` 命令仍然可用（标记为legacy）
- 向后兼容，不影响现有工作流
