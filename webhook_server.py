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

# Server start time for uptime tracking
server_start_time = datetime.now()

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
        # Check if tmux session exists
        result = subprocess.run(
            ['tmux', 'has-session', '-t', TMUX_SESSION],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.info(f"Tmux session '{TMUX_SESSION}' does not exist")
            return False

        # Check if Claude Code is actually running in the session
        output = subprocess.check_output(
            ['tmux', 'capture-pane', '-t', TMUX_SESSION, '-p'],
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
            logger.info(f"Claude Code is running in session '{TMUX_SESSION}'")
            return True
        else:
            logger.info(f"Tmux session '{TMUX_SESSION}' exists but Claude Code is not running")
            return False
    except Exception as e:
        logger.error(f"Error checking Claude session: {e}")
        return False

def start_claude_session():
    """Start Claude Code session in tmux"""
    try:
        logger.info(f"Starting Claude Code session in tmux '{TMUX_SESSION}'")

        # Check if session already exists
        result = subprocess.run(
            ['tmux', 'has-session', '-t', TMUX_SESSION],
            capture_output=True
        )

        if result.returncode == 0:
            # Session exists, kill it first
            logger.info(f"Session '{TMUX_SESSION}' already exists, killing it")
            subprocess.run(['tmux', 'kill-session', '-t', TMUX_SESSION], check=False)
            time.sleep(1)

        # Create new tmux session and start claude
        subprocess.run(
            ['tmux', 'new-session', '-d', '-s', TMUX_SESSION, 'claude'],
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
        logger.info(f"Sending task to Claude Code: {task[:50]}...")

        # Send the task to tmux session
        subprocess.run(
            ['tmux', 'send-keys', '-t', TMUX_SESSION, task, 'C-m'],
            check=True
        )

        # Wait a moment for the text to be entered
        time.sleep(0.5)

        # Send another Enter to submit the prompt
        subprocess.run(
            ['tmux', 'send-keys', '-t', TMUX_SESSION, 'C-m'],
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
                output = subprocess.check_output(
                    ['tmux', 'capture-pane', '-t', TMUX_SESSION, '-p'],
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
            subprocess.run(['tmux', 'kill-session', '-t', TMUX_SESSION],
                         check=True)
            send_telegram_message("✓ Claude Code 会话已停止")
        except subprocess.CalledProcessError:
            send_telegram_message("✗ 会话不存在或停止失败")
        except Exception as e:
            send_telegram_message(f"✗ 错误: {e}")

    elif cmd == '/status':
        # Get recent tmux output
        try:
            output = subprocess.check_output(
                ['tmux', 'capture-pane', '-t', TMUX_SESSION, '-p'],
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

    elif cmd == '/help':
        help_text = """【可用命令】

───────────────────
§ 交互会话:
• /ask <任务> → 发送任务到 Claude Code（自动启动会话）
• /session → 查看会话状态
• /start_claude → 手动启动 Claude Code 会话
• /stop_claude → 停止 Claude Code 会话

§ 监控:
• /status → 当前 tmux 输出
• /last_output → 完整最后响应

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
            subprocess.run(
                ['tmux', 'send-keys', '-t', TMUX_SESSION,
                 actual_command, 'C-m'],
                check=True
            )
            send_telegram_message(f"""✓ 命令已发送到 Claude Code

→ 命令: {actual_command}""")
        except Exception as e:
            send_telegram_message(f"✗ 发送命令失败: {e}")

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
