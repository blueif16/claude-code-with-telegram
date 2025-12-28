# 多项目架构使用指南

## 架构概述

系统采用主服务器 + 子服务器架构：

```
Telegram Bot
    ↓
主 Webhook 服务器 (端口 8000)
    ↓
子 Webhook 服务器 (端口 8001, 8002, ...)
    ↓
各自 tmux 会话中的 Claude Code
```

### 组件说明

1. **主 Webhook 服务器** (`webhook_server.py`)
   - 端口: 8000
   - 接收 Telegram 命令
   - 管理项目切换
   - 显示所有项目状态

2. **子 Webhook 服务器** (`sub_webhook_server.py`)
   - 每个项目一个实例
   - 运行在各自的 tmux 会话中
   - 直接与该会话的 Claude Code 交互
   - 独立端口 (8001, 8002, ...)

## 快速开始

### 1. 配置项目

编辑 `config.json`，添加项目配置：

```json
{
  "projects": {
    "current": "default",
    "list": {
      "default": {
        "name": "默认项目",
        "tmux_session": "claude",
        "sub_server_port": 8001,
        "path": "/path/to/project"
      },
      "project-a": {
        "name": "项目 A",
        "tmux_session": "claude-a",
        "sub_server_port": 8002,
        "path": "/path/to/project-a"
      }
    }
  }
}
```

### 2. 启动主服务器

```bash
python3 webhook_server.py
```

### 3. 为每个项目启动子服务器

```bash
# 为 claude 会话启动子服务器
./start_sub_server.sh claude 8001

# 为其他项目启动子服务器
./start_sub_server.sh claude-a 8002
```

### 4. 验证服务器状态

```bash
# 检查主服务器
curl http://localhost:8000/health

# 检查子服务器
curl http://localhost:8001/health
curl http://localhost:8002/health
```

## Telegram 命令

### 查看所有项目

```
/projects
```

显示：
- 所有运行中的 tmux 会话
- 每个会话的窗口数和附加状态
- 子服务器运行状态（🟢 运行中 | 🔴 未运行 | ⚪ 未配置）
- 可点击的按钮切换项目

### 切换项目

点击 `/projects` 命令返回的按钮，或使用：

```
/switch <session_name>
```

### 发送任务到当前项目

```
/ask <任务描述>
```

任务会发送到当前活跃项目的 Claude Code。

### 查看当前会话状态

```
/session
```

## 子服务器 API

每个子服务器提供以下端点：

### GET /health
健康检查

响应：
```json
{
  "status": "ok",
  "port": 8001,
  "tmux_session": "claude",
  "session_active": true,
  "uptime_seconds": 123
}
```

### POST /ask
发送任务到 Claude Code

请求：
```json
{
  "task": "分析这个文件"
}
```

响应：
```json
{
  "ok": true,
  "message": "Task sent to claude"
}
```

### POST /answer
发送回答（用于 AskUserQuestion）

请求：
```json
{
  "answer": "选项 A"
}
```

### GET /status
获取 tmux 输出

响应：
```json
{
  "ok": true,
  "tmux_session": "claude",
  "output": "最近20行输出..."
}
```

## 日志文件

- 主服务器: `logs/webhook.log`
- 子服务器: `logs/sub_webhook_<session_name>.log`

查看日志：
```bash
tail -f logs/webhook.log
tail -f logs/sub_webhook_claude.log
```

## 故障排查

### 子服务器未运行

症状：`/projects` 显示 🔴

解决：
```bash
./start_sub_server.sh <session_name> <port>
```

### tmux 会话不存在

症状：子服务器启动失败

解决：
```bash
tmux new-session -s <session_name>
```

### 端口被占用

症状：子服务器启动失败，提示端口占用

解决：
```bash
# 查找占用端口的进程
lsof -i :<port>

# 停止进程
kill -9 <pid>
```

## 测试脚本

```bash
# 测试 /projects 命令
./tests/test_projects_command.sh

# 测试会话切换
./tests/test_session_switch.sh
```

## 架构优势

1. **隔离性**: 每个项目有独立的子服务器和 tmux 会话
2. **可扩展**: 轻松添加新项目，只需配置和启动子服务器
3. **独立性**: 一个项目崩溃不影响其他项目
4. **灵活性**: 可以为不同项目配置不同的通知级别
5. **可见性**: 通过 `/projects` 命令一目了然地查看所有项目状态
