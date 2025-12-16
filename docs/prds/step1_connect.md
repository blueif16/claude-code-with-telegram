# 📋 Claude Code + Telegram Bot 双向通信系统 PRD

## 🎯 项目目标

构建一个可靠的双向通信系统：
- **Claude Code → Telegram**：实时通知任务进度（包含实际输出）
- **Telegram → Claude Code**：远程发送命令和查询状态

---

## 📊 阶段划分

```
Stage 1: 本地验证阶段 (Local Testing)
├── 目标：确保所有组件在本地网络通信正常
├── 时长：2-4 小时
└── 成功标准：本地 curl 能触发 Telegram 通知，Telegram 能控制本地命令

Stage 2: 公网接入阶段 (Cloudflare Integration)
├── 目标：通过 Cloudflare Tunnel 实现公网访问
├── 时长：2-3 小时
└── 成功标准：手机上的 Telegram 能完整控制远程 Claude Code
```

---

## 🔧 Hook 数据结构

### Claude Code Hooks 实际接收的数据

Claude Code hooks 通过 **stdin 接收 JSON 格式的上下文数据**：

```json
// Stop Hook 接收:
{
  "response": "Claude's actual response text here...",
  "timestamp": "2025-12-14T10:30:00Z",
  "duration_ms": 1234,
  "tool_calls": [
    {
      "tool": "Bash",
      "input": {...},
      "output": "..."
    }
  ]
}

// PostToolUse Hook 接收:
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "ls -la",
    "description": "List files"
  },
  "tool_output": "total 48\ndrwxr-xr-x  12 user  staff  384 Dec 14 10:30 .",
  "timestamp": "2025-12-14T10:30:00Z"
}

// SubagentStop Hook 接收:
{
  "subagent_type": "explore",
  "description": "Search for error handling",
  "result": "Found 3 files with error handling...",
  "duration_ms": 5678,
  "timestamp": "2025-12-14T10:30:00Z"
}
```

---

## 🔧 Stage 1: 本地验证阶段

### 前置准备检查清单

```
✅ Python 3.8+ 已安装
✅ tmux 已安装
✅ 已从 @BotFather 获得 Bot Token
✅ 已获得你的 Chat ID
✅ 有一台运行 Linux/macOS 的机器
```

### 获取 Chat ID 的详细步骤

```
1. 打开 Telegram，搜索你的 bot（@your_bot_name）
2. 点击 START 或发送任意消息（如 "hello"）
3. 在浏览器打开：
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
4. 在返回的 JSON 中找到：
   {
     "message": {
       "chat": {
         "id": 123456789  ← 这就是你的 Chat ID
       }
     }
   }
5. 记录这个数字
```

---

### 1.1 环境准备

#### 目录结构

```bash
claude-telegram-bot/
├── webhook_server.py           # Webhook 服务器
├── notify-telegram-smart.sh    # 智能通知脚本
├── config.json                 # 配置文件
├── requirements.txt            # Python 依赖
└── logs/                       # 日志目录
    ├── webhook.log
    ├── hooks.log
    └── last_output.json
```

#### 创建目录

```bash
mkdir -p ~/claude-telegram-bot/logs
cd ~/claude-telegram-bot
```

---

### 1.2 配置文件

#### config.json

```json
{
  "telegram": {
    "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "chat_id": "你的_CHAT_ID",
    "secret_token": "your-secret-token-change-this"
  },
  "webhook": {
    "host": "127.0.0.1",
    "port": 8000,
    "path": {
      "telegram": "/telegram-webhook",
      "claude": "/claude-hook"
    }
  },
  "claude": {
    "tmux_session": "claude",
    "allowed_commands": ["status", "help", "screenshot", "read_log", "last_output"]
  },
  "security": {
    "allowed_chat_ids": ["你的_CHAT_ID"],
    "command_whitelist": true,
    "dangerous_commands": ["rm", "dd", "format", "shutdown"]
  }
}
```

---

### 1.3 智能通知脚本

创建 `~/.claude/notify-telegram-smart.sh`:

```bash
#!/bin/bash

# This script receives JSON via stdin from Claude Code hooks
# and sends formatted notifications to Telegram

EVENT_TYPE="$1"  # "stop", "tool_use", "subagent", etc.

# Read JSON from stdin
INPUT_JSON=$(cat)

# Extract key information based on event type
case "$EVENT_TYPE" in
  "stop")
    # Extract Claude's response and metadata
    RESPONSE=$(echo "$INPUT_JSON" | jq -r '.response // "No response"' | head -c 500)
    DURATION=$(echo "$INPUT_JSON" | jq -r '.duration_ms // 0')
    TIMESTAMP=$(echo "$INPUT_JSON" | jq -r '.timestamp // "Unknown"')
    
    MESSAGE="✅ *Task Completed*

*Duration:* ${DURATION}ms
*Time:* ${TIMESTAMP}

*Response Preview:*
\`\`\`
${RESPONSE}
\`\`\`

_Use /last_output for full response_"
    ;;
    
  "tool_use")
    # Extract tool execution details
    TOOL=$(echo "$INPUT_JSON" | jq -r '.tool_name // "Unknown"')
    TOOL_INPUT=$(echo "$INPUT_JSON" | jq -r '.tool_input | tostring' | head -c 200)
    TOOL_OUTPUT=$(echo "$INPUT_JSON" | jq -r '.tool_output // "No output"' | head -c 300)
    
    MESSAGE="🔧 *Tool Executed*

*Tool:* $TOOL

*Input:*
\`\`\`
${TOOL_INPUT}
\`\`\`

*Output Preview:*
\`\`\`
${TOOL_OUTPUT}
\`\`\`"
    ;;
    
  "subagent")
    # Extract subagent results
    SUBAGENT=$(echo "$INPUT_JSON" | jq -r '.subagent_type // "Unknown"')
    DESC=$(echo "$INPUT_JSON" | jq -r '.description // "No description"')
    RESULT=$(echo "$INPUT_JSON" | jq -r '.result // "No result"' | head -c 400)
    DURATION=$(echo "$INPUT_JSON" | jq -r '.duration_ms // 0')
    
    MESSAGE="🤖 *Subagent Completed*

*Type:* $SUBAGENT
*Task:* $DESC
*Duration:* ${DURATION}ms

*Result Preview:*
\`\`\`
${RESULT}
\`\`\`"
    ;;
    
  "notification")
    # For generic notifications
    MSG=$(echo "$INPUT_JSON" | jq -r '.message // "Notification"')
    MESSAGE="⚠️ *Notification*

${MSG}"
    ;;
    
  *)
    MESSAGE="ℹ️ Event: $EVENT_TYPE

$(echo "$INPUT_JSON" | jq '.')"
    ;;
esac

# Save to local log for /last_output command
echo "$INPUT_JSON" > ~/.claude/last_output.json

# Send to webhook
curl -X POST http://localhost:8000/claude-hook \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg event "$EVENT_TYPE" \
    --arg message "$MESSAGE" \
    --argjson raw_data "$INPUT_JSON" \
    '{event: $event, message: $message, raw_data: $raw_data}'
  )" \
  --max-time 5 \
  --retry 2 \
  --retry-delay 1 \
  2>> ~/.claude/hooks.log

# Exit with success
exit 0
```

```bash
chmod +x ~/.claude/notify-telegram-smart.sh
```

---

### 1.4 Webhook 服务器

创建 `~/claude-telegram-bot/webhook_server.py`:

```python
#!/usr/bin/env python3
import json
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
import requests
import subprocess

# Configuration
CONFIG = json.load(open('config.json'))
BOT_TOKEN = CONFIG['telegram']['bot_token']
CHAT_ID = CONFIG['telegram']['chat_id']
SECRET_TOKEN = CONFIG['telegram']['secret_token']
TMUX_SESSION = CONFIG['claude']['tmux_session']

# Setup
app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/webhook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Storage for last outputs (simple in-memory for MVP)
last_outputs = {
    'stop': None,
    'tool_use': None,
    'subagent': None
}

def send_telegram_message(text, parse_mode='Markdown'):
    """Send message to Telegram with retry"""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    
    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Telegram message sent: {response.json().get('result', {}).get('message_id')}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        raise

@app.route('/claude-hook', methods=['POST'])
def claude_hook():
    """Receive notifications from Claude Code hooks"""
    try:
        data = request.get_json()
        event = data.get('event', 'unknown')
        message = data.get('message', 'No message')
        raw_data = data.get('raw_data', {})
        
        logger.info(f"Received Claude hook: {event}")
        
        # Store last output for retrieval
        if event in last_outputs:
            last_outputs[event] = {
                'timestamp': datetime.now().isoformat(),
                'data': raw_data,
                'message': message
            }
        
        # Send to Telegram
        send_telegram_message(message)
        
        return jsonify({'ok': True}), 200
        
    except Exception as e:
        logger.error(f"Error in claude_hook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Receive commands from Telegram"""
    # Verify secret token
    token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if token != SECRET_TOKEN:
        logger.warning(f"Invalid token from {request.remote_addr}")
        return jsonify({'error': 'Invalid token'}), 403
    
    try:
        data = request.get_json()
        message = data.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        
        # Verify chat_id
        if str(chat_id) != str(CHAT_ID):
            logger.warning(f"Unauthorized chat_id: {chat_id}")
            return jsonify({'ok': False}), 403
        
        logger.info(f"Received command: {text}")
        
        # Handle commands
        if text.startswith('/'):
            handle_command(text)
        
        return jsonify({'ok': True}), 200
        
    except Exception as e:
        logger.error(f"Error in telegram_webhook: {e}")
        return jsonify({'error': str(e)}), 500

def handle_command(command):
    """Execute commands from Telegram"""
    cmd = command.lower().strip()
    
    if cmd == '/status':
        # Get recent tmux output
        try:
            output = subprocess.check_output(
                ['tmux', 'capture-pane', '-t', TMUX_SESSION, '-p'],
                text=True
            )
            last_lines = '\n'.join(output.split('\n')[-20:])
            send_telegram_message(f"📊 *Current Status:*\n\n```\n{last_lines}\n```")
        except Exception as e:
            send_telegram_message(f"❌ Error getting status: {e}")
        
    elif cmd == '/last_output':
        # Send last stored output
        if last_outputs['stop']:
            data = last_outputs['stop']
            msg = f"📄 *Last Complete Output*\n\n"
            msg += f"*Time:* {data['timestamp']}\n\n"
            response_text = data.get('data', {}).get('response', 'No output')
            msg += f"```\n{response_text[:1000]}\n```"
            send_telegram_message(msg)
        else:
            send_telegram_message("No recent output available")
            
    elif cmd == '/help':
        help_text = """🤖 *Available Commands:*

/status - Current tmux output
/last_output - Full last response
/help - This message

Send `/claude <command>` to execute in Claude Code"""
        send_telegram_message(help_text)
        
    elif cmd.startswith('/claude '):
        # Send command to Claude Code tmux session
        actual_command = command[8:]  # Remove '/claude '
        try:
            subprocess.run(
                ['tmux', 'send-keys', '-t', TMUX_SESSION, actual_command, 'C-m'],
                check=True
            )
            send_telegram_message(f"✅ Command sent to Claude Code:\n`{actual_command}`")
        except Exception as e:
            send_telegram_message(f"❌ Error sending command: {e}")
        
    else:
        send_telegram_message(f"Unknown command. Send /help for available commands.")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'last_outputs': {k: v is not None for k, v in last_outputs.items()}
    }), 200

if __name__ == '__main__':
    logger.info("Starting webhook server...")
    app.run(host='127.0.0.1', port=8000, debug=False)
```

#### requirements.txt

```
flask==3.0.0
requests==2.31.0
```

安装依赖：
```bash
cd ~/claude-telegram-bot
pip3 install -r requirements.txt
```

---

### 1.5 Claude Code Hooks 配置

#### 理解 Hooks 数据流

```
Claude Code 任务完成
    ↓
Hook 事件触发
    ↓
JSON 数据通过 stdin 发送给 hook command
    ↓
我们的脚本读取 stdin (cat)
    ↓
解析 JSON 并格式化
    ↓
发送到 Webhook
    ↓
Webhook 转发到 Telegram
```

#### Hooks 配置详解

编辑 `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "~/.claude/notify-telegram-smart.sh stop"
      }]
    }],
    
    "PostToolUse": [{
      "matcher": "Bash|Read|Write|Edit",
      "hooks": [{
        "type": "command", 
        "command": "~/.claude/notify-telegram-smart.sh tool_use"
      }]
    }],
    
    "SubagentStop": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "~/.claude/notify-telegram-smart.sh subagent"
      }]
    }],
    
    "Notification": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "jq -n --arg msg \"$(cat -)\" '{message:$msg}' | ~/.claude/notify-telegram-smart.sh notification"
      }]
    }]
  }
}
```

#### 关键说明

**1. Stop Hook**
```json
{
  "type": "command",
  "command": "~/.claude/notify-telegram-smart.sh stop"
}
```
- Claude Code 会自动把 JSON 数据通过 stdin 传给这个命令
- JSON 包含: `{"response": "...", "duration_ms": 123, "timestamp": "..."}`
- 脚本内部用 `INPUT_JSON=$(cat)` 读取这个 JSON

**2. PostToolUse Hook**
```json
{
  "matcher": "Bash|Read|Write|Edit",
  "command": "~/.claude/notify-telegram-smart.sh tool_use"
}
```
- 只在这些工具执行后触发
- JSON 包含: `{"tool_name": "Bash", "tool_input": {...}, "tool_output": "..."}`

**3. SubagentStop Hook**
```json
{
  "command": "~/.claude/notify-telegram-smart.sh subagent"
}
```
- Subagent 完成时触发
- JSON 包含: `{"subagent_type": "explore", "description": "...", "result": "..."}`

**4. Notification Hook**
```json
{
  "command": "jq -n --arg msg \"$(cat -)\" '{message:$msg}' | ~/.claude/notify-telegram-smart.sh notification"
}
```
- 这个比较特殊，因为 Notification 事件可能不直接提供 JSON
- 我们用 `jq` 把文本包装成 JSON 格式

#### 验证 Hooks 配置

```bash
# 1. 检查配置文件语法
cat ~/.claude/settings.json | jq '.'

# 如果有语法错误，jq 会报错

# 2. 测试单个 Hook（模拟 Claude Code 发送 JSON）
echo '{"response":"Test response","duration_ms":1234,"timestamp":"2025-12-14T10:30:00Z"}' | \
  ~/.claude/notify-telegram-smart.sh stop

# 3. 查看 Hook 是否被正确注册
# 启动 Claude Code 后，hooks 会自动加载
# 检查日志看是否有加载错误
```

#### Hooks 数据示例

**Stop Hook 实际接收的 JSON:**
```json
{
  "response": "I've analyzed the log file. Found 3 errors:\n1. Database connection timeout at 10:23\n2. API rate limit exceeded at 10:45\n3. Memory allocation failure at 11:12\n\nRecommendations:\n- Increase connection pool size\n- Implement exponential backoff\n- Add memory monitoring",
  "timestamp": "2025-12-14T11:15:30Z",
  "duration_ms": 45230
}
```

**PostToolUse Hook 实际接收的 JSON:**
```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "grep -r 'ERROR' logs/app.log | wc -l",
    "description": "Count error lines in log file"
  },
  "tool_output": "42",
  "timestamp": "2025-12-14T11:14:50Z"
}
```

**SubagentStop Hook 实际接收的 JSON:**
```json
{
  "subagent_type": "explore",
  "description": "Search for authentication logic",
  "result": "Found authentication in 3 locations:\n1. src/auth/login.ts - Main login handler\n2. src/middleware/auth.ts - JWT verification\n3. src/utils/password.ts - Password hashing\n\nKey findings:\n- Using bcrypt for password hashing\n- JWT tokens expire after 24 hours\n- No rate limiting on login endpoint",
  "duration_ms": 12450,
  "timestamp": "2025-12-14T11:10:15Z"
}
```

---

### 1.6 本地测试流程

#### 测试 1: 启动 Webhook 服务器

```bash
# 终端 1
cd ~/claude-telegram-bot
python3 webhook_server.py

# 预期输出：
# * Running on http://127.0.0.1:8000
# * Webhook server started
```

#### 测试 2: Claude Hook → Telegram 通知

```bash
# 终端 2: 模拟 Stop Hook
echo '{"response":"Test task completed","duration_ms":1234,"timestamp":"2025-12-14T10:30:00Z"}' | \
  ~/.claude/notify-telegram-smart.sh stop

# 验证点：
# ✅ Telegram 收到格式化的消息
# ✅ 包含实际的响应文本
# ✅ 包含时长和时间戳
```

#### 测试 3: 创建 tmux Session

```bash
# 终端 3
tmux new-session -d -s claude

# 验证
tmux list-sessions | grep claude
```

#### 测试 4: Telegram → Webhook 接收

```bash
# 终端 2: 模拟 Telegram 命令
curl -X POST http://127.0.0.1:8000/telegram-webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: your-secret-token-change-this" \
  -d '{
    "message": {
      "chat": {
        "id": 你的_CHAT_ID
      },
      "text": "/status"
    }
  }'

# 验证点：
# ✅ curl 返回 200
# ✅ Telegram 收到 tmux 输出
```

#### 测试 5: 端到端流程

```bash
# 在 Telegram App 中：
1. 发送: /status
   → 应该收到当前 tmux 输出

2. 发送: /help
   → 应该收到帮助信息

3. 发送: /claude echo "test"
   → 命令应该在 tmux 中执行

# 验证 tmux 中的命令
tmux capture-pane -t claude -p | tail -5
```

---

### 1.7 Stage 1 完成标准

```
✅ 必须通过的测试：

1. Webhook 服务器稳定运行
2. 本地 curl 触发通知，Telegram 正确接收（延迟 < 2s）
3. 通知包含实际的 Claude 输出（不只是通用消息）
4. Telegram 发送命令，webhook 正确解析
5. tmux 命令执行成功
6. /status 返回实际 tmux 输出
7. /last_output 返回完整响应
8. 所有日志正常记录

❌ 如果以下任一失败，不要进入 Stage 2：
- Telegram 消息延迟 > 5 秒
- 收到的是通用消息而不是实际输出
- tmux 命令执行失败
- 出现未处理的异常
```

---

## 🌐 Stage 2: Cloudflare Tunnel 集成

### 2.1 Cloudflare Tunnel 设置

#### 安装 cloudflared

**macOS:**
```bash
brew install cloudflare/cloudflare/cloudflared
```

**Linux:**
```bash
# Debian/Ubuntu
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

#### 登录和创建 Tunnel

```bash
# 登录
cloudflared tunnel login

# 创建 tunnel
cloudflared tunnel create claude-bot

# 记录 Tunnel ID: abc-123-def-456

# 配置 DNS
cloudflared tunnel route dns claude-bot webhook.你的域名.com
```

#### 配置文件

创建 `~/.cloudflared/config.yml`:

```yaml
tunnel: abc-123-def-456
credentials-file: /home/你的用户名/.cloudflared/abc-123-def-456.json

ingress:
  - hostname: webhook.你的域名.com
    service: http://localhost:8000
  - service: http_status:404
```

#### 启动 Tunnel

```bash
cloudflared tunnel run claude-bot

# 成功输出：
# INF Registered tunnel connection
```

---

### 2.2 配置 Telegram Webhook

```bash
curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
  -d "url=https://webhook.你的域名.com/telegram-webhook" \
  -d "secret_token=your-secret-token-change-this"

# 验证
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

---

### 2.3 Stage 2 测试

#### 测试 1: 公网通知

```bash
# Claude Code Hook 仍然用本地地址
echo '{"response":"Public test","duration_ms":999}' | \
  ~/.claude/notify-telegram-smart.sh stop

# 验证：手机 Telegram 收到消息
```

#### 测试 2: 远程命令

```
在手机 Telegram 发送：
/status

# 应该收到实际的 tmux 输出
```

#### 测试 3: 完整流程

```
1. 在 Claude Code 中执行任务
2. 任务完成时 Stop Hook 触发
3. 手机收到通知（包含实际输出）
4. 发送 /last_output 查看完整响应
```

---

### 2.4 生产部署

创建 systemd services：

```bash
# Webhook Service
sudo nano /etc/systemd/system/claude-webhook.service
```

```ini
[Unit]
Description=Claude Telegram Webhook
After=network.target

[Service]
Type=simple
User=你的用户名
WorkingDirectory=/home/你的用户名/claude-telegram-bot
ExecStart=/usr/bin/python3 webhook_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Cloudflare Tunnel Service
sudo nano /etc/systemd/system/cloudflare-tunnel.service
```

```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=你的用户名
ExecStart=/usr/local/bin/cloudflared tunnel run claude-bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动
sudo systemctl enable claude-webhook cloudflare-tunnel
sudo systemctl start claude-webhook cloudflare-tunnel
```

---

## 📊 MVP 功能范围

### ✅ 包含的功能

**通知内容：**
- 实际的 Claude 响应文本（前 500 字符预览）
- 任务完成时间戳
- 执行时长（毫秒）
- 工具执行详情（命令 + 输出）
- Subagent 执行结果

**命令功能：**
- `/status` - 当前 tmux 输出
- `/last_output` - 完整的最后响应
- `/help` - 帮助信息
- `/claude <command>` - 远程执行命令

### ❌ MVP 不包含

- 完整的对话历史
- Token 使用统计
- 详细的错误追踪
- 性能指标监控

---

## 🎯 最终验收标准

```
✅ 功能测试：
□ Claude Code 任务完成时发送通知（包含实际输出）
□ 通知包含时间戳和时长
□ 从 Telegram 发送 /status 获取当前状态
□ 从 Telegram 发送 /last_output 获取完整响应
□ 远程命令正确执行

✅ 性能测试：
□ 本地通知延迟 < 2 秒
□ 公网命令延迟 < 5 秒
□ 24 小时运行无崩溃

✅ 安全测试：
□ 错误的 secret_token 被拒绝
□ 错误的 chat_id 被拒绝
□ 日志中无敏感信息泄露
```

---

## 🚨 故障排查

### 问题 1: Telegram 收不到消息

```bash
# 测试 Bot Token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# 手动发送测试
curl -X POST https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage \
  -d "chat_id=<YOUR_CHAT_ID>" \
  -d "text=Test"
```

### 问题 2: Hook 没有触发

```bash
# 检查脚本权限
ls -la ~/.claude/notify-telegram-smart.sh

# 测试 Hook 脚本
echo '{"response":"test"}' | ~/.claude/notify-telegram-smart.sh stop

# 检查日志
tail -f ~/.claude/hooks.log
```

### 问题 3: Webhook 收不到请求

```bash
# 检查端口
lsof -i :8000

# 检查进程
ps aux | grep webhook_server.py

# 查看日志
tail -f ~/claude-telegram-bot/logs/webhook.log
```

---

## 📚 附录

### 快速命令参考

```bash
# 启动服务
python3 ~/claude-telegram-bot/webhook_server.py
cloudflared tunnel run claude-bot

# 查看状态
systemctl status claude-webhook
systemctl status cloudflare-tunnel

# 查看日志
tail -f ~/claude-telegram-bot/logs/webhook.log
tail -f ~/.claude/hooks.log

# 测试 Hook
echo '{"response":"test","duration_ms":123}' | \
  ~/.claude/notify-telegram-smart.sh stop
```

### Telegram 命令速查

```
/status       - 查看当前状态
/last_output  - 完整的最后输出
/help         - 帮助信息
/claude cmd   - 远程执行命令
```