#!/usr/bin/env python3
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
import requests
import subprocess
import shutil

# Check for required dependencies
def check_dependencies():
    """Check if required system dependencies are installed"""
    missing = []

    if not shutil.which('tmux'):
        missing.append('tmux')
    if not shutil.which('jq'):
        missing.append('jq')

    if missing:
        print(f"❌ 缺少依赖: {', '.join(missing)}")
        print(f"请运行: ./setup.sh")
        sys.exit(1)

check_dependencies()

# Configuration
CONFIG = json.load(open('config.json'))
BOT_TOKEN = CONFIG['telegram']['bot_token']
CHAT_ID = CONFIG['telegram']['chat_id']
SECRET_TOKEN = CONFIG['telegram']['secret_token']
TMUX_SESSION = CONFIG['claude']['tmux_session']

# Multi-project support
PROJECTS = CONFIG.get('projects', {})
CURRENT_PROJECT = PROJECTS.get('current', 'default')
PROJECT_LIST = PROJECTS.get('list', {})

# Test mode - set TEST_MODE=1 to disable Telegram API calls
TEST_MODE = os.environ.get('TEST_MODE', '0') == '1'

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

if TEST_MODE:
    logger.info("🧪 TEST MODE ENABLED - Telegram API calls will be simulated")

# Storage for last outputs (simple in-memory for MVP)
last_outputs = {
    'stop': None,
    'tool_use': None,
    'subagent': None
}

# History storage configuration
HISTORY_FILE = Path('logs/history.json')
MAX_HISTORY_ENTRIES = 100

# Server start time for uptime tracking
server_start_time = datetime.now()

def get_current_project_config():
    """获取当前项目配置"""
    global CURRENT_PROJECT, PROJECT_LIST
    if CURRENT_PROJECT in PROJECT_LIST:
        return PROJECT_LIST[CURRENT_PROJECT]
    return None

def get_current_tmux_session():
    """获取当前项目的tmux会话名"""
    project_config = get_current_project_config()
    if project_config:
        return project_config.get('tmux_session', TMUX_SESSION)
    return TMUX_SESSION

def switch_project(project_id):
    """切换到指定项目"""
    global CURRENT_PROJECT
    if project_id not in PROJECT_LIST:
        return False, f"项目 '{project_id}' 不存在"

    CURRENT_PROJECT = project_id

    # 更新配置文件
    CONFIG['projects']['current'] = project_id
    with open('config.json', 'w') as f:
        json.dump(CONFIG, f, indent=2, ensure_ascii=False)

    return True, f"已切换到项目: {PROJECT_LIST[project_id]['name']}"

def load_history():
    """Load history from JSON file"""
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Failed to load history: {e}")
        return []

def save_history(history):
    """Save history to JSON file"""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save history: {e}")
        return False

def add_to_history(event_type, message, raw_data):
    """Add entry to history with size limit"""
    history = load_history()

    entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'message': message,
        'raw_data': raw_data
    }

    history.append(entry)

    # Keep only last MAX_HISTORY_ENTRIES
    if len(history) > MAX_HISTORY_ENTRIES:
        history = history[-MAX_HISTORY_ENTRIES:]

    save_history(history)
    return entry

def get_history(limit=10, event_type=None):
    """Get history entries with optional filtering"""
    history = load_history()

    # Filter by event type if specified
    if event_type:
        history = [h for h in history if h.get('event_type') == event_type]

    # Return last N entries
    return history[-limit:] if limit else history

def check_telegram_api():
    """Check Telegram API connectivity"""
    if TEST_MODE:
        return {
            'reachable': True,
            'test_mode': True
        }

    try:
        url = f'https://api.telegram.org/bot{BOT_TOKEN}/getMe'
        response = requests.get(url, timeout=5)
        response.raise_for_status()

        result = response.json()
        if result.get('ok'):
            bot_info = result.get('result', {})
            return {
                'reachable': True,
                'bot_username': bot_info.get('username'),
                'bot_id': bot_info.get('id')
            }
        else:
            return {
                'reachable': False,
                'error': 'API returned ok=false'
            }
    except requests.exceptions.Timeout:
        return {
            'reachable': False,
            'error': 'Timeout after 5s'
        }
    except requests.exceptions.ConnectionError:
        return {
            'reachable': False,
            'error': 'Connection failed'
        }
    except Exception as e:
        return {
            'reachable': False,
            'error': str(e)
        }

def check_tmux_server_status():
    """Check tmux server status for health endpoint"""
    try:
        result = subprocess.run(
            ['tmux', 'list-sessions'],
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode == 0:
            session_count = len([l for l in result.stdout.strip().split('\n') if l])
            return {
                'running': True,
                'sessions': session_count,
                'socket': f"/private/tmp/tmux-{os.getuid()}/default"
            }
        elif 'no server running' in result.stderr.lower():
            return {
                'running': False,
                'error': 'No server running'
            }
        else:
            return {
                'running': True,
                'sessions': 0
            }
    except Exception as e:
        return {
            'running': False,
            'error': str(e)
        }

def ensure_tmux_server():
    """Ensure tmux server is running, start if necessary"""
    try:
        # Check if tmux server is running by listing sessions
        result = subprocess.run(
            ['tmux', 'list-sessions'],
            capture_output=True,
            text=True
        )

        # If command succeeds or fails with "no sessions" message, server is running
        if result.returncode == 0 or 'no server running' not in result.stderr.lower():
            logger.info("Tmux server is running")
            return True

        # Server not running, try to start it
        logger.warning("Tmux server not running, attempting to start...")

        # Create and immediately kill a dummy session to start the server
        subprocess.run(
            ['tmux', 'new-session', '-d', '-s', 'tmux-init-dummy'],
            check=True,
            capture_output=True
        )
        subprocess.run(
            ['tmux', 'kill-session', '-t', 'tmux-init-dummy'],
            check=False,
            capture_output=True
        )

        # Verify server is now running
        result = subprocess.run(
            ['tmux', 'list-sessions'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 or 'no server running' not in result.stderr.lower():
            logger.info("✅ Tmux server started successfully")
            return True
        else:
            logger.error("❌ Failed to start tmux server")
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"Error starting tmux server: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error with tmux server: {e}")
        return False

def perform_startup_health_check():
    """Perform comprehensive health check on startup"""
    logger.info("=" * 60)
    logger.info("Starting comprehensive health check...")
    logger.info("=" * 60)

    health_status = {
        'tmux_server': None,
        'telegram_api': None,
        'overall': 'unknown'
    }

    # Check tmux server
    logger.info("Checking tmux server...")
    if ensure_tmux_server():
        tmux_status = check_tmux_server_status()
        health_status['tmux_server'] = tmux_status
        if tmux_status.get('running'):
            logger.info(f"✅ Tmux server: OK ({tmux_status.get('sessions', 0)} sessions)")
        else:
            logger.warning(f"⚠️  Tmux server: {tmux_status.get('error', 'Unknown error')}")
    else:
        health_status['tmux_server'] = {'running': False, 'error': 'Failed to start'}
        logger.error("❌ Tmux server: FAILED")

    # Check Telegram API
    logger.info("Checking Telegram API connectivity...")
    telegram_status = check_telegram_api()
    health_status['telegram_api'] = telegram_status

    if telegram_status.get('reachable'):
        if telegram_status.get('test_mode'):
            logger.info("✅ Telegram API: TEST MODE")
        else:
            logger.info(f"✅ Telegram API: OK (@{telegram_status.get('bot_username')})")
    else:
        logger.error(f"❌ Telegram API: {telegram_status.get('error', 'Unknown error')}")

    # Determine overall status
    tmux_ok = health_status['tmux_server'] and health_status['tmux_server'].get('running')
    telegram_ok = health_status['telegram_api'] and health_status['telegram_api'].get('reachable')

    if tmux_ok and telegram_ok:
        health_status['overall'] = 'healthy'
        logger.info("=" * 60)
        logger.info("✅ Health check PASSED - All systems operational")
        logger.info("=" * 60)
    elif tmux_ok or telegram_ok:
        health_status['overall'] = 'degraded'
        logger.warning("=" * 60)
        logger.warning("⚠️  Health check DEGRADED - Some systems have issues")
        logger.warning("=" * 60)

        # Send alert to Telegram if Telegram is working
        if telegram_ok:
            try:
                alert_msg = "⚠️ Webhook Server Health Alert\n\n"
                if not tmux_ok:
                    alert_msg += "❌ Tmux server: Not running\n"
                alert_msg += "\nServer started but some components need attention."
                send_telegram_message(alert_msg)
            except Exception as e:
                logger.error(f"Failed to send health alert: {e}")
    else:
        health_status['overall'] = 'unhealthy'
        logger.error("=" * 60)
        logger.error("❌ Health check FAILED - Critical systems down")
        logger.error("=" * 60)

    return health_status

def send_telegram_message(text, parse_mode=None):
    """Send message to Telegram with retry"""
    if TEST_MODE:
        # In test mode, just log the message instead of sending to Telegram
        logger.info(f"📤 [TEST MODE] Would send to Telegram:\n{text}")
        return {'ok': True, 'result': {'message_id': 'test_mode'}}

    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'

    payload = {
        'chat_id': CHAT_ID,
        'text': text,
        'disable_web_page_preview': True
    }

    if parse_mode:
        payload['parse_mode'] = parse_mode

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Telegram message sent: {response.json().get('result', {}).get('message_id')}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        raise

def check_claude_session():
    """Check if Claude Code session is running"""
    try:
        tmux_session = get_current_tmux_session()
        # Check if tmux session exists
        result = subprocess.run(
            ['tmux', 'has-session', '-t', tmux_session],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.info(f"Tmux session '{tmux_session}' does not exist")
            return False

        # Check if Claude Code is actually running in the session
        output = subprocess.check_output(
            ['tmux', 'capture-pane', '-t', tmux_session, '-p'],
            text=True
        )

        # Look for Claude Code indicators in the output
        # Claude Code typically shows prompts or is waiting for input
        has_claude = any([
            'claude>' in output.lower(),
            'claude code' in output.lower(),
            'anthropic' in output.lower(),
            # Check if the last command was 'claude'
            output.strip().endswith('claude')
        ])

        if has_claude:
            logger.info(f"Claude Code is running in session '{tmux_session}'")
            return True
        else:
            logger.info(f"Tmux session '{tmux_session}' exists but Claude Code is not running")
            return False
    except Exception as e:
        logger.error(f"Error checking Claude session: {e}")
        return False

def start_claude_session():
    """Start Claude Code session in tmux"""
    try:
        tmux_session = get_current_tmux_session()
        project_config = get_current_project_config()
        project_path = project_config.get('path') if project_config else None

        logger.info(f"Starting Claude Code session in tmux '{tmux_session}'")

        # Check if session already exists
        result = subprocess.run(
            ['tmux', 'has-session', '-t', tmux_session],
            capture_output=True
        )

        if result.returncode == 0:
            # Session exists, kill it first
            logger.info(f"Session '{tmux_session}' already exists, killing it")
            subprocess.run(['tmux', 'kill-session', '-t', tmux_session], check=False)
            time.sleep(1)

        # Create new tmux session and start claude
        if project_path:
            # Start in project directory
            subprocess.run(
                ['tmux', 'new-session', '-d', '-s', tmux_session, '-c', project_path, 'claude'],
                check=True
            )
        else:
            # Start in current directory
            subprocess.run(
                ['tmux', 'new-session', '-d', '-s', tmux_session, 'claude'],
                check=True
            )

        # Wait for Claude Code to start
        time.sleep(3)

        # Verify Claude Code is running
        if check_claude_session():
            logger.info("Claude Code session started and verified")
            return True
        else:
            logger.warning("Claude Code session created but verification failed")
            return True  # Still return True as session was created

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to start Claude session: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error starting Claude session: {e}")
        return False

def send_task_to_claude(task):
    """Send task to Claude Code via tmux"""
    try:
        tmux_session = get_current_tmux_session()
        logger.info(f"Sending task to Claude Code: {task[:50]}...")

        # Send the task to tmux session
        subprocess.run(
            ['tmux', 'send-keys', '-t', tmux_session, task, 'C-m'],
            check=True
        )

        # Wait a moment for the text to be entered
        time.sleep(0.5)

        # Send another Enter to submit the prompt
        subprocess.run(
            ['tmux', 'send-keys', '-t', tmux_session, 'C-m'],
            check=True
        )

        logger.info("Task sent and submitted successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to send task: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending task: {e}")
        return False

def should_notify(event, raw_data):
    """智能过滤：决定是否发送通知到Telegram"""
    notification_config = CONFIG.get('notification', {})
    level = notification_config.get('level', 'normal')
    always_notify = notification_config.get('always_notify_events', ['stop', 'error', 'permission', 'question'])
    silent_tools = notification_config.get('silent_tools', ['Read', 'Grep', 'Glob', 'Edit', 'Write', 'Bash', 'Task'])
    silent_events = notification_config.get('silent_events', [])

    # 总是通知的重要事件
    if event in always_notify:
        return True

    # 检查是否在静默事件列表中
    if event in silent_events:
        logger.info(f"Silencing event: {event}")
        return False

    # tool_use事件：检查工具是否在静默列表中
    if event == 'tool_use':
        tool_name = raw_data.get('tool_name', '')
        if tool_name in silent_tools:
            logger.info(f"Silencing tool: {tool_name}")
            return False
        return True

    # subagent事件：根据level决定
    if event == 'subagent':
        if level == 'minimal':
            return False
        return True

    # 其他事件：根据level决定
    if level == 'minimal':
        return False

    return True

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

        # Add to persistent history
        add_to_history(event, message, raw_data)

        # 智能过滤：只发送重要通知
        if should_notify(event, raw_data):
            send_telegram_message(message)
            logger.info(f"✓ Notification sent for event: {event}")
        else:
            logger.info(f"✗ Notification silenced for event: {event}")

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

    if cmd.startswith('/ask '):
        # Extract task description
        task = command[5:].strip()

        if not task:
            send_telegram_message("✗ 请提供任务描述\n\n用法: /ask <你的问题或任务>")
            return

        if len(task) > 1000:
            send_telegram_message("✗ 任务描述过长（最多1000字符）")
            return

        # Check session status
        if not check_claude_session():
            send_telegram_message("◐ Claude Code会话未运行，正在启动...")
            if not start_claude_session():
                send_telegram_message("✗ 启动会话失败，请检查日志或使用 /start_claude")
                return
            send_telegram_message("✓ 会话启动成功")

        # Send task
        if send_task_to_claude(task):
            msg = f"""✓ 任务已发送到 Claude Code

任务内容:
───────────────────
{task[:200]}{'...' if len(task) > 200 else ''}
───────────────────

◐ 执行中... 你将收到进度通知"""
            send_telegram_message(msg)
        else:
            send_telegram_message("✗ 发送任务失败，请查看日志")

    elif cmd == '/session':
        # Check session status
        session_exists = check_claude_session()

        if session_exists:
            try:
                tmux_session = get_current_tmux_session()
                output = subprocess.check_output(
                    ['tmux', 'capture-pane', '-t', tmux_session, '-p'],
                    text=True
                )
                last_lines = '\n'.join(output.split('\n')[-10:])

                msg = f"""【会话状态】

✓ Tmux会话: 运行中
✓ Claude Code: 活跃

最近输出:
───────────────────
{last_lines}
───────────────────

※ 使用 /ask 发送任务"""
                send_telegram_message(msg)
            except Exception as e:
                send_telegram_message(f"✓ 会话运行中\n✗ 无法获取输出: {e}")
        else:
            send_telegram_message("""✗ 会话未运行

※ 使用 /start_claude 手动启动
  或使用 /ask <任务> 自动启动并执行""")

    elif cmd == '/start_claude':
        if check_claude_session():
            send_telegram_message("✓ Claude Code会话已在运行\n\n※ 使用 /ask 发送任务")
        else:
            send_telegram_message("◐ 正在启动 Claude Code 会话...")
            if start_claude_session():
                send_telegram_message("""✓ 会话启动成功

现在可以使用:
• /ask <任务> → 发送任务到 Claude Code
• /session → 查看会话状态""")
            else:
                send_telegram_message("✗ 启动会话失败，请查看日志")

    elif cmd == '/stop_claude':
        try:
            tmux_session = get_current_tmux_session()
            subprocess.run(['tmux', 'kill-session', '-t', tmux_session],
                         check=True)
            send_telegram_message("✓ Claude Code 会话已停止")
        except subprocess.CalledProcessError:
            send_telegram_message("✗ 会话不存在或停止失败")
        except Exception as e:
            send_telegram_message(f"✗ 错误: {e}")

    elif cmd == '/status':
        # Get recent tmux output
        try:
            tmux_session = get_current_tmux_session()
            output = subprocess.check_output(
                ['tmux', 'capture-pane', '-t', tmux_session, '-p'],
                text=True
            )
            last_lines = '\n'.join(output.split('\n')[-20:])
            send_telegram_message(f"""【当前状态】

───────────────────
{last_lines}
───────────────────""")
        except Exception as e:
            send_telegram_message(f"✗ 获取状态失败: {e}")

    elif cmd == '/last_output':
        # Send last stored output
        if last_outputs['stop']:
            data = last_outputs['stop']
            timestamp = data['timestamp'].split('T')[1].split('.')[0]
            msg = f"""【最后完整输出】

✓ 时间: {timestamp}

───────────────────
{data.get('data', {}).get('response', '无输出')[:1000]}
───────────────────"""
            send_telegram_message(msg)
        else:
            send_telegram_message("○ 暂无最近输出")

    elif cmd == '/last':
        # Get last history entry (any type)
        history = get_history(limit=1)
        if history:
            entry = history[0]
            msg = f"📄 最近一条记录\n\n"
            msg += f"⏰ 时间: {entry['timestamp']}\n"
            msg += f"🏷️ 类型: {entry['event_type']}\n\n"
            msg += f"📝 内容:\n{entry['message'][:800]}"
            if len(entry['message']) > 800:
                msg += "\n\n... (内容过长已截断)"
            send_telegram_message(msg)
        else:
            send_telegram_message("暂无历史记录")

    elif cmd.startswith('/history'):
        # Parse command: /history [limit] [type]
        parts = command.split()
        limit = 10
        event_type = None

        # Parse arguments
        if len(parts) > 1:
            try:
                limit = int(parts[1])
                limit = min(limit, 50)  # Max 50 entries
            except ValueError:
                # Maybe it's a type filter
                event_type = parts[1]

        if len(parts) > 2:
            event_type = parts[2]

        # Get history
        history = get_history(limit=limit, event_type=event_type)

        if not history:
            msg = "暂无历史记录"
            if event_type:
                msg += f" (类型: {event_type})"
            send_telegram_message(msg)
            return

        # Format message
        msg = f"📚 历史记录 (最近{len(history)}条"
        if event_type:
            msg += f", 类型: {event_type}"
        msg += ")\n\n"

        for i, entry in enumerate(reversed(history), 1):
            timestamp = entry['timestamp'].split('T')[1][:8]  # HH:MM:SS
            event = entry['event_type']
            preview = entry['message'][:60].replace('\n', ' ')
            msg += f"{i}. [{timestamp}] {event}\n   {preview}...\n\n"

        msg += "\n💡 使用 /last 查看最近一条完整记录"
        send_telegram_message(msg)

    elif cmd == '/help':
        help_text = """【可用命令】

───────────────────
§ 交互会话:
• /ask <任务> → 发送任务到 Claude Code（自动启动会话）
• /session → 查看会话状态
• /start_claude → 手动启动 Claude Code 会话
• /stop_claude → 停止 Claude Code 会话

§ 多项目支持:
• /projects → 列出所有项目
• /switch <项目ID> → 切换到指定项目

§ 监控:
• /status → 当前 tmux 输出
• /last_output → 完整最后响应 (legacy)
• /last → 最近一条记录 (任意类型)
• /history [N] [type] → 历史记录列表
  例: /history 20 - 显示最近20条
  例: /history stop - 只显示stop类型
  例: /history 15 tool_use - 显示15条tool_use

§ 其他:
• /help → 显示此帮助
• /claude <命令> → 在 tmux 中执行命令

───────────────────
※ 示例:
  /ask 分析 webhook_server.py 文件"""
        send_telegram_message(help_text)

    elif cmd.startswith('/claude '):
        # Send command to Claude Code tmux session
        actual_command = command[8:]  # Remove '/claude '
        try:
            tmux_session = get_current_tmux_session()
            subprocess.run(
                ['tmux', 'send-keys', '-t', tmux_session,
                 actual_command, 'C-m'],
                check=True
            )
            send_telegram_message(f"""✓ 命令已发送到 Claude Code

→ 命令: {actual_command}""")
        except Exception as e:
            send_telegram_message(f"✗ 发送命令失败: {e}")

    elif cmd == '/projects':
        # List all projects
        if not PROJECT_LIST:
            send_telegram_message("✗ 未配置项目")
            return

        msg = "📁 可用项目:\n\n"
        for project_id, project_info in PROJECT_LIST.items():
            is_current = "✓ " if project_id == CURRENT_PROJECT else "  "
            name = project_info.get('name', project_id)
            desc = project_info.get('description', '无描述')
            path = project_info.get('path', 'N/A')
            msg += f"{is_current}{project_id}\n"
            msg += f"  名称: {name}\n"
            msg += f"  描述: {desc}\n"
            msg += f"  路径: {path}\n\n"

        msg += f"\n当前项目: {CURRENT_PROJECT}\n"
        msg += "\n使用 /switch <项目ID> 切换项目"
        send_telegram_message(msg)

    elif cmd.startswith('/switch '):
        # Switch project
        project_id = command[8:].strip()

        if not project_id:
            msg = "✗ 请指定项目ID\n\n"
            msg += "用法: /switch <项目ID>\n\n"
            msg += "使用 /projects 查看可用项目"
            send_telegram_message(msg)
            return

        success, message = switch_project(project_id)

        if success:
            msg = f"✓ {message}\n\n"
            msg += "注意: 需要重启Claude Code会话才能在新项目目录中工作\n"
            msg += "使用 /start_claude 启动新会话"
            send_telegram_message(msg)
        else:
            send_telegram_message(f"✗ {message}\n\n使用 /projects 查看可用项目")

    else:
        send_telegram_message("✗ 未知命令\n\n※ 发送 /help 查看可用命令")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    tmux_status = check_tmux_server_status()
    telegram_status = check_telegram_api()

    # Calculate uptime
    uptime_seconds = (datetime.now() - server_start_time).total_seconds()
    uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"

    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'uptime': uptime_str,
        'uptime_seconds': int(uptime_seconds),
        'tmux_server': tmux_status,
        'telegram_api': telegram_status,
        'last_outputs': {k: v is not None for k, v in last_outputs.items()}
    }), 200

if __name__ == '__main__':
    logger.info("Starting webhook server...")

    # Perform comprehensive health check
    health_status = perform_startup_health_check()

    # Start server regardless of health check result
    # (degraded mode is acceptable)
    app.run(host='127.0.0.1', port=8000, debug=False)
