# Claude Code + Telegram 双向通信系统

通过 Telegram Bot 实现 Claude Code 的远程监控和控制，支持实时通知、远程命令执行和交互式问答。

## 核心特性

- **实时通知**: Claude Code 任务完成、工具使用、子代理执行自动推送到 Telegram
- **远程控制**: 通过 Telegram 发送命令到 Claude Code tmux session
- **交互式问答**: AskUserQuestion 通过 Telegram 按钮回答，无需手动输入
- **后台运行**: 基于 tmux 的非阻塞架构，支持真正的后台执行

## 最近更新

### dbed863 - 多项目系统升级
- 新增多项目支持：可管理多个 Claude Code 会话
- 直接消息发送：非命令消息自动发送到当前项目
- 项目切换：`/projects` 命令显示所有项目，点击按钮切换
- 子服务器架构：每个项目运行独立的子服务器（端口隔离）
- 配置文件扩展：`config.json` 新增 `projects` 配置段

**新增命令**:
- `/projects` - 列出所有运行中的项目和子服务器状态
- `/switch <项目ID>` - 切换到指定项目
- 直接发送消息 - 自动发送到当前项目的 Claude Code

**架构说明**:
- 主服务器 (8000): 处理 Telegram 通信和路由
- 子服务器 (动态端口): 每个 tmux 会话一个，处理项目级别的交互
- 当前场景 (单机单用户): 子服务器可选，主服务器可直接操作 tmux
- 未来场景 (跨机器/多用户/容器化): 子服务器必需
- 详见: [docs/architecture/sub-server-justification.md](docs/architecture/sub-server-justification.md)

## 系统架构

### 架构概览

**简化架构 (当前单机场景)**:
```
Telegram ←→ 主服务器 ←→ tmux (多个 session)
                         ├─ claude (项目 A)
                         ├─ project-b (项目 B)
                         └─ project-c (项目 C)
```

**完整架构 (多机器/容器化场景)**:
```
Telegram ←→ 主服务器 ←→ 子服务器A (机器A/容器A) ←→ tmux
                     ├─ 子服务器B (机器B/容器B) ←→ tmux
                     └─ 子服务器C (机器C/容器C) ←→ tmux
```

### 通信流程可视化

#### 1. Claude Code → Telegram 通知流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code (tmux session)                  │
│                                                                   │
│  用户任务 → 执行工具 → 完成任务                                 │
│              ↓          ↓         ↓                              │
│         PostToolUse  SubagentStop Stop                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Hook 触发
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              .claude/notify-telegram-smart.sh                    │
│                                                                   │
│  1. 接收 JSON (via stdin)                                        │
│  2. 解析事件类型 (stop/tool_use/subagent/notification)          │
│  3. 格式化消息内容                                               │
│  4. 提取关键信息 (duration, tool_name, output, etc.)            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP POST
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              webhook_server.py (Flask)                           │
│                                                                   │
│  POST /claude-hook                                               │
│  ├─ 接收格式化的消息数据                                        │
│  ├─ 存储到 last_output (用于 /last_output 命令)                │
│  └─ 调用 Telegram Bot API                                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Telegram Bot API                               │
│                                                                   │
│  sendMessage(chat_id, text)                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                   用户的 Telegram 客户端                         │
│                                                                   │
│  📱 收到通知消息                                                 │
│  ✅ 任务完成: 耗时 1.2s                                          │
│  🔧 工具使用: Bash - git status                                 │
│  🤖 子代理完成: Explore agent                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 2. Telegram → Claude Code 命令执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                   用户的 Telegram 客户端                         │
│                                                                   │
│  用户输入: /status                                               │
│  用户输入: /claude echo "hello"                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Telegram Bot API                               │
│                                                                   │
│  POST /telegram-webhook                                          │
│  Headers: X-Telegram-Bot-Api-Secret-Token                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              webhook_server.py (Flask)                           │
│                                                                   │
│  POST /telegram-webhook                                          │
│  ├─ 验证 secret_token                                           │
│  ├─ 验证 chat_id (安全检查)                                     │
│  ├─ 解析命令类型                                                │
│  │   ├─ /status → tmux capture-pane                             │
│  │   ├─ /last_output → 返回存储的输出                           │
│  │   ├─ /claude <cmd> → tmux send-keys                          │
│  │   └─ /help → 返回帮助信息                                    │
│  └─ 执行命令并返回结果                                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ tmux send-keys / capture-pane
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code (tmux session)                  │
│                                                                   │
│  接收命令 → 执行 → 返回结果                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 结果通过 tmux capture
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              webhook_server.py → Telegram API                    │
│                                                                   │
│  sendMessage(chat_id, result)                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                   用户的 Telegram 客户端                         │
│                                                                   │
│  📱 收到命令执行结果                                             │
└─────────────────────────────────────────────────────────────────┘
```

#### 3. AskUserQuestion 交互式问答流程

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code (tmux session)                  │
│                                                                   │
│  执行任务 → 调用 AskUserQuestion                                │
│              ↓                                                    │
│         触发 Notification hook (idle_prompt)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Hook 触发 (JSON with questions data)
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              .claude/notify-telegram-smart.sh                    │
│                                                                   │
│  1. 检测到 idle_prompt 事件                                      │
│  2. 提取 questions 数组                                          │
│  3. 解析每个问题的 question, header, options                    │
│  4. 标记 is_question=true                                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP POST (is_question=true)
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              webhook_server.py (Flask)                           │
│                                                                   │
│  POST /claude-hook (is_question=true)                            │
│  ├─ 解析 questions 数据                                         │
│  ├─ 为每个问题生成 inline_keyboard                              │
│  │   └─ 每个 option 生成一个按钮                                │
│  │       callback_data: question_index:option_label              │
│  └─ 调用 Telegram sendMessage with reply_markup                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                   用户的 Telegram 客户端                         │
│                                                                   │
│  📱 收到问题消息                                                 │
│  ❓ Which language do you prefer?                                │
│  ┌──────────┬──────────┬──────────┐                             │
│  │ Python   │   Go     │   Rust   │  ← Inline Keyboard          │
│  └──────────┴──────────┴──────────┘                             │
│                                                                   │
│  用户点击 "Python" 按钮                                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ callback_query
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              webhook_server.py (Flask)                           │
│                                                                   │
│  POST /telegram-webhook (callback_query)                         │
│  ├─ 解析 callback_data: "0:Python"                              │
│  ├─ 提取 question_index=0, answer="Python"                      │
│  ├─ 构造答案 JSON: {"0": "Python"}                              │
│  ├─ 通过 tmux send-keys 发送到 claude session                   │
│  │   tmux send-keys -t claude '{"0":"Python"}' C-m              │
│  └─ 回复 answerCallbackQuery (显示 "✅ 已选择: Python")         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ tmux send-keys
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code (tmux session)                  │
│                                                                   │
│  AskUserQuestion 等待中...                                       │
│  ↓                                                                │
│  接收到答案: {"0": "Python"}                                     │
│  ↓                                                                │
│  解析答案并继续执行任务                                          │
│  ↓                                                                │
│  基于用户选择生成响应                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. webhook_server.py (Flask 服务器)
- **端口**: 8000
- **端点**:
  - `POST /claude-hook`: 接收 Claude Code hooks 通知
  - `POST /telegram-webhook`: 接收 Telegram 命令和回调
  - `GET /health`: 健康检查
  - `GET /last_output`: 获取最后一次输出

#### 2. .claude/notify-telegram-smart.sh (Hook 脚本)
- 接收 Claude Code hooks 的 JSON 输入
- 解析事件类型: stop, tool_use, subagent, notification
- 格式化消息并发送到 webhook 服务器
- 特殊处理 AskUserQuestion (idle_prompt 事件)

#### 3. config.json (配置文件)
```json
{
  "telegram": {
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID",
    "secret_token": "YOUR_SECRET"
  },
  "webhook": {
    "host": "127.0.0.1",
    "port": 8000
  },
  "claude": {
    "tmux_session": "claude"
  }
}
```

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 配置 Telegram Bot

1. 与 @BotFather 对话创建 bot，获取 `bot_token`
2. 获取你的 `chat_id`:
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
3. 编辑 `config.json`，填入 bot_token 和 chat_id

### 3. 启动系统 (Tmux 模式)

**重要**: 必须在 tmux 中运行 Claude Code 才能实现完整的双向通信。

使用自动化脚本:
```bash
chmod +x start_all.sh stop_all.sh
./start_all.sh
```

或手动启动:
```bash
# 1. 启动 webhook 服务器
tmux new-session -d -s webhook-server
tmux send-keys -t webhook-server "cd $(pwd) && python3 webhook_server.py" C-m

# 2. 启动 Claude Code
tmux new-session -d -s claude
tmux send-keys -t claude "cd $(pwd) && claude" C-m

# 3. (可选) 启动 Cloudflare tunnel 用于公网访问
tmux new-session -d -s cloudflare-tunnel
tmux send-keys -t cloudflare-tunnel "cloudflared tunnel run claude-bot" C-m
```

### 4. 验证系统

```bash
# 检查 webhook 服务器
curl http://localhost:8000/health

# 查看 tmux sessions
tmux list-sessions

# 测试完整流程
./tests/test_local_only.sh
```

## Telegram 命令

### 交互会话
| 命令 | 说明 | 示例 |
|------|------|------|
| `/ask <任务>` | 发送任务到 Claude Code (自动启动会话) | `/ask 分析 webhook_server.py` |
| `/session` | 查看会话状态 | `/session` |
| `/start_claude` | 手动启动 Claude Code 会话 | `/start_claude` |
| `/stop_claude` | 停止 Claude Code 会话 | `/stop_claude` |

### 多项目支持
| 命令 | 说明 | 示例 |
|------|------|------|
| `/projects` | 列出所有项目和子服务器状态 | `/projects` |
| `/switch <项目ID>` | 切换到指定项目 | `/switch default` |
| 直接发送消息 | 发送到当前项目的 Claude Code | `帮我优化这段代码` |

### 监控
| 命令 | 说明 | 示例 |
|------|------|------|
| `/status` | 获取 Claude Code 当前输出 (最后 20 行) | `/status` |
| `/last_output` | 获取完整的最后一次响应 (legacy) | `/last_output` |
| `/last` | 最近一条记录 (任意类型) | `/last` |
| `/history [N] [type]` | 历史记录列表 | `/history 20 stop` |

### 其他
| 命令 | 说明 | 示例 |
|------|------|------|
| `/claude <命令>` | 在 Claude Code session 中执行命令 | `/claude echo "test"` |
| `/help` | 显示帮助信息 | `/help` |

## Tmux 会话管理

```bash
# 查看所有 sessions
tmux list-sessions

# 附加到 Claude Code session (查看实时输出)
tmux attach -t claude

# 附加到 webhook 服务器 (查看日志)
tmux attach -t webhook-server

# 分离当前 session (不关闭)
Ctrl+B, D

# 捕获 session 输出 (不附加)
tmux capture-pane -t claude -p

# 向 session 发送命令
tmux send-keys -t claude "echo test" C-m

# 停止 session
tmux kill-session -t claude
```

## 日志查看

```bash
# Webhook 服务器日志
tail -f logs/webhook.log

# Claude Code hooks 日志
tail -f ~/.claude/hooks.log

# 实时监控所有日志
tail -f logs/webhook.log ~/.claude/hooks.log
```

## 测试

```bash
# 测试 Telegram API 连接
./tests/test_telegram.sh

# 测试 Hook → Webhook → Telegram 流程
./tests/test_hook.sh

# 测试 Telegram → Webhook 流程
./tests/test_webhook.sh

# 测试完整本地流程 (无外部依赖)
./tests/test_local_only.sh

# 手动测试 hook
echo '{"response":"test","duration_ms":123}' | ./.claude/notify-telegram-smart.sh stop
```

## 文件结构

```
claude-code-with-telegram/
├── webhook_server.py              # 主 Flask 服务器 (1268 行)
├── sub_webhook_server.py          # 子服务器 (195 行，可选)
├── config.json                    # 配置文件 (包含密钥)
├── requirements.txt               # Python 依赖
├── start_all.sh                   # 启动所有服务 (主+子服务器)
├── start_sub_server.sh            # 启动单个子服务器
├── stop_all.sh                    # 停止所有服务
├── .claude/
│   ├── notify-telegram-smart.sh   # Hook 脚本
│   ├── settings.json              # Claude Code hooks 配置
│   └── settings.local.json        # 本地配置覆盖
├── tests/                         # 测试脚本
│   ├── test_telegram.sh
│   ├── test_hook.sh
│   ├── test_webhook.sh
│   └── test_local_only.sh
├── logs/                          # 日志目录
│   ├── webhook.log                # 主服务器日志
│   ├── sub_webhook_*.log          # 子服务器日志
│   └── history.json               # 历史记录
├── docs/                          # 文档
│   ├── prds/                      # 产品需求文档
│   └── architecture/              # 架构文档
│       └── sub-server-justification.md  # 子服务器存在性分析
└── templates/                     # 模板文件
    └── cute.md                    # Commit 消息模板
```

## 安全说明

- Webhook 验证 `X-Telegram-Bot-Api-Secret-Token` header
- 只有配置的 `chat_id` 可以发送命令
- 危险命令 (rm, dd, format, shutdown) 已加入黑名单
- 可通过 `security.command_whitelist` 启用命令白名单

## 常见问题

### Telegram 收不到消息
1. 检查 `config.json` 中的 bot_token 和 chat_id
2. 运行测试: `./tests/test_telegram.sh`
3. 查看日志: `tail -f logs/webhook.log`

### Hooks 没有触发
1. 检查脚本权限: `ls -la .claude/notify-telegram-smart.sh`
2. 手动测试: `echo '{"response":"test"}' | ./.claude/notify-telegram-smart.sh stop`
3. 查看 hooks 日志: `tail -f ~/.claude/hooks.log`

### Webhook 收不到请求
1. 检查端口占用: `lsof -i :8000`
2. 确认服务运行: `ps aux | grep webhook_server.py`
3. 测试健康检查: `curl http://localhost:8000/health`

### AskUserQuestion 没有响应
1. 确认 Claude Code 在 tmux session "claude" 中运行
2. 检查 tmux session: `tmux list-sessions | grep claude`
3. 查看 webhook 日志确认收到 callback: `tail -f logs/webhook.log | grep callback`
4. 手动测试 tmux send-keys: `tmux send-keys -t claude "test" C-m`

## 高级功能

### 多窗口 Tmux 布局

在单个 session 中运行所有服务:

```bash
# 创建 session 并命名第一个窗口
tmux new-session -d -s claude-system -n webhook
tmux send-keys -t claude-system:webhook "python3 webhook_server.py" C-m

# 创建第二个窗口运行 Claude Code
tmux new-window -t claude-system -n claude
tmux send-keys -t claude-system:claude "claude" C-m

# 创建第三个窗口监控日志
tmux new-window -t claude-system -n logs
tmux send-keys -t claude-system:logs "tail -f logs/webhook.log" C-m

# 附加到 session
tmux attach -t claude-system

# 切换窗口: Ctrl+B, 0/1/2
```

### 测试模式

禁用实际的 Telegram API 调用 (仅记录日志):

```bash
TEST_MODE=1 python3 webhook_server.py
```

## 贡献

欢迎提交 Issue 和 Pull Request!

## 许可证

MIT License
