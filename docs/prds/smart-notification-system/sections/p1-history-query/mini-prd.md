# P1 - 历史查询

## 目标

实现按需查询工具调用历史的功能，让用户可以主动查看执行细节，而不是被动接收所有通知。

## 前置依赖

- P0 的 tool_history 存储已实现

## 范围

### 1. 实现 /history 命令
- 支持按工具类型过滤：`/history bash`
- 支持按事件类型过滤：`/history error`
- 支持时间范围：`/history 1h`（最近1小时）
- 无参数时返回最近10条记录

### 2. 实现 /last 命令
- `/last` 或 `/last 1`：返回最后一条记录的详细信息
- `/last 5`：返回最近5条记录
- 包含完整的输入输出内容

### 3. 历史记录持久化
- 将 tool_history 保存到文件（JSON格式）
- 服务器启动时加载历史记录
- 实现自动清理（保留最近1000条）

### 4. 格式化输出
- 简洁模式：只显示时间、事件类型、工具名称
- 详细模式：包含输入输出内容
- 支持 Telegram 的 Markdown 格式

## 验收标准

- [ ] /history 命令返回最近10条记录
- [ ] /history bash 只返回 bash 工具的记录
- [ ] /history error 只返回错误事件
- [ ] /history 1h 返回最近1小时的记录
- [ ] /last 返回最后一条记录的详细信息
- [ ] /last 5 返回最近5条记录
- [ ] 历史记录保存到 logs/tool_history.json
- [ ] 服务器重启后历史记录保留
- [ ] 自动清理超过1000条的旧记录
- [ ] 输出格式清晰易读

## 上下文边界

**拥有:**
- webhook_server.py（添加 /history 和 /last 处理逻辑）
- logs/tool_history.json（历史记录文件）

**读取:**
- config.json（配置项）
- P0 实现的 tool_history 变量

**禁止:**
- .claude/notify-telegram-smart.sh
- tests/*

## 实现细节

### Telegram 命令处理
```python
def handle_telegram_command(message):
    text = message.get('text', '')

    if text.startswith('/history'):
        args = text.split()[1:] if len(text.split()) > 1 else []
        return handle_history_query(args)

    elif text.startswith('/last'):
        n = int(text.split()[1]) if len(text.split()) > 1 else 1
        return handle_last_query(n)
```

### 历史查询逻辑
```python
def handle_history_query(args):
    filtered = tool_history.copy()

    # 按工具类型过滤
    if args and args[0] in ['bash', 'read', 'write', 'edit', 'grep']:
        filtered = [h for h in filtered if h.get('tool') == args[0]]

    # 按事件类型过滤
    elif args and args[0] in ['stop', 'error', 'tool_use']:
        filtered = [h for h in filtered if h.get('event') == args[0]]

    # 按时间范围过滤
    elif args and args[0].endswith('h'):
        hours = int(args[0][:-1])
        cutoff = datetime.now() - timedelta(hours=hours)
        filtered = [h for h in filtered
                   if datetime.fromisoformat(h['timestamp']) > cutoff]

    # 返回最近10条
    return format_history(filtered[-10:])
```

### 持久化
```python
HISTORY_FILE = 'logs/tool_history.json'
MAX_HISTORY = 1000

def save_history():
    with open(HISTORY_FILE, 'w') as f:
        json.dump(tool_history[-MAX_HISTORY:], f, indent=2)

def load_history():
    global tool_history
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            tool_history = json.load(f)
```

### 格式化输出
```python
def format_history(records, detailed=False):
    if not records:
        return "📜 没有找到历史记录"

    lines = ["📜 历史记录：\n"]
    for r in records:
        time = r['timestamp'].split('T')[1][:8]
        event = r['event']
        tool = r.get('tool', 'N/A')

        if detailed:
            lines.append(f"⏰ {time} | {event} | {tool}")
            if 'input' in r:
                lines.append(f"  📥 输入: {r['input'][:100]}")
            if 'output' in r:
                lines.append(f"  📤 输出: {r['output'][:100]}")
        else:
            lines.append(f"⏰ {time} | {event} | {tool}")

    return "\n".join(lines)
```

## 测试计划

1. 执行多个工具调用，验证历史记录正确存储
2. 测试 /history 返回最近10条
3. 测试 /history bash 只返回 bash 记录
4. 测试 /last 返回详细信息
5. 重启服务器，验证历史记录保留
6. 添加超过1000条记录，验证自动清理
