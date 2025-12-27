# P2 - 多项目支持

## 目标

支持同时管理多个 Claude Code 项目，允许用户在不同项目间切换，并为每个项目配置独立的通知级别。

## 前置依赖

- P0 的智能过滤已实现
- P1 的历史查询已实现

## 范围

### 1. 多项目配置结构
扩展 config.json 支持多项目：
```json
{
  "projects": {
    "project-a": {
      "name": "Telegram Bot",
      "path": "/path/to/project-a",
      "tmux_session": "claude-a",
      "notification_level": "normal"
    },
    "project-b": {
      "name": "Web API",
      "path": "/path/to/project-b",
      "tmux_session": "claude-b",
      "notification_level": "minimal"
    }
  },
  "active_project": "project-a"
}
```

### 2. 项目切换命令
- `/projects`：列出所有项目及其状态
- `/switch <project-id>`：切换活跃项目
- `/ask@<project-id> <任务>`：向特定项目发送任务

### 3. 项目状态监控
- 显示每个项目的 tmux 会话状态
- 显示最后活动时间
- 显示当前通知级别

### 4. 独立历史记录
- 每个项目维护独立的历史记录
- 历史查询默认针对当前活跃项目
- 支持跨项目查询：`/history@project-b bash`

## 验收标准

- [ ] config.json 支持 projects 配置结构
- [ ] /projects 命令列出所有项目及状态
- [ ] /switch 命令切换活跃项目
- [ ] /ask@project-id 向指定项目发送任务
- [ ] 每个项目有独立的 notification_level
- [ ] 每个项目有独立的历史记录文件
- [ ] /history 默认查询当前项目
- [ ] /history@project-id 查询指定项目
- [ ] 项目切换延迟 < 2秒
- [ ] 显示每个项目的 tmux 会话状态

## 上下文边界

**拥有:**
- webhook_server.py（添加多项目管理逻辑）
- config.json（扩展为多项目配置）
- logs/tool_history_<project-id>.json（每个项目的历史）

**读取:**
- P0 的通知过滤逻辑
- P1 的历史查询逻辑

**禁止:**
- .claude/notify-telegram-smart.sh（不需要修改）
- tests/*

## 实现细节

### 项目管理类
```python
class ProjectManager:
    def __init__(self, config_path='config.json'):
        self.config = self.load_config(config_path)
        self.projects = self.config.get('projects', {})
        self.active_project = self.config.get('active_project')

    def get_active_project(self):
        return self.projects.get(self.active_project)

    def switch_project(self, project_id):
        if project_id not in self.projects:
            raise ValueError(f"项目 {project_id} 不存在")
        self.active_project = project_id
        self.save_config()

    def get_project_status(self, project_id):
        project = self.projects[project_id]
        tmux_session = project['tmux_session']
        # 检查 tmux 会话是否存在
        result = subprocess.run(
            ['tmux', 'has-session', '-t', tmux_session],
            capture_output=True
        )
        return {
            'name': project['name'],
            'active': result.returncode == 0,
            'notification_level': project['notification_level']
        }
```

### 命令处理
```python
def handle_telegram_command(message):
    text = message.get('text', '')

    if text == '/projects':
        return handle_projects_list()

    elif text.startswith('/switch '):
        project_id = text.split()[1]
        return handle_project_switch(project_id)

    elif '@' in text and text.startswith('/ask@'):
        # /ask@project-b 重构代码
        parts = text.split(' ', 1)
        project_id = parts[0].split('@')[1]
        task = parts[1] if len(parts) > 1 else ''
        return handle_project_task(project_id, task)
```

### 项目列表显示
```python
def handle_projects_list():
    lines = ["📁 项目列表：\n"]
    for pid, project in pm.projects.items():
        status = pm.get_project_status(pid)
        active_mark = "✅" if pid == pm.active_project else "  "
        status_mark = "🟢" if status['active'] else "🔴"
        level = status['notification_level']

        lines.append(
            f"{active_mark} {status_mark} {project['name']} "
            f"({pid}) - {level}"
        )

    return "\n".join(lines)
```

### 独立历史记录
```python
def get_history_file(project_id=None):
    pid = project_id or pm.active_project
    return f'logs/tool_history_{pid}.json'

def save_history(project_id=None):
    file_path = get_history_file(project_id)
    with open(file_path, 'w') as f:
        json.dump(tool_history, f, indent=2)
```

## 测试计划

1. 配置两个项目，验证配置加载正确
2. 测试 /projects 显示所有项目状态
3. 测试 /switch 切换项目
4. 测试 /ask@project-b 向指定项目发送任务
5. 验证每个项目有独立的历史记录文件
6. 验证每个项目的通知级别独立生效
7. 测试跨项目历史查询
