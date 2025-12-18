#!/usr/bin/env python3
import json
import logging
import os
import time
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
            send_telegram_message("❌ Please provide a task description\n\nUsage: /ask <your question or task>")
            return

        if len(task) > 1000:
            send_telegram_message("❌ Task description too long (max 1000 characters)")
            return

        # Check session status
        if not check_claude_session():
            send_telegram_message("🚀 Claude Code session not running, starting now...")
            if not start_claude_session():
                send_telegram_message("❌ Failed to start session. Please check logs or use /start_claude")
                return
            send_telegram_message("✅ Session started successfully")

        # Send task
        if send_task_to_claude(task):
            msg = f"""✅ Task sent to Claude Code

📝 Task:
{task[:200]}{'...' if len(task) > 200 else ''}

⏳ Executing... You will receive progress notifications"""
            send_telegram_message(msg)
        else:
            send_telegram_message("❌ Failed to send task. Check logs for details")

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

                msg = f"""📊 Session Status

✅ Tmux Session: Running
✅ Claude Code: Active

Recent output:
```
{last_lines}
```

Use /ask to send a task"""
                send_telegram_message(msg)
            except Exception as e:
                send_telegram_message(f"✅ Session running\n❌ Cannot get output: {e}")
        else:
            send_telegram_message("""❌ Session not running

Use /start_claude to start manually
Or use /ask <task> to auto-start and execute""")

    elif cmd == '/start_claude':
        if check_claude_session():
            send_telegram_message("✅ Claude Code session is already running\n\nUse /ask to send a task")
        else:
            send_telegram_message("🚀 Starting Claude Code session...")
            if start_claude_session():
                send_telegram_message("""✅ Session started successfully

Now you can use:
/ask <task> - Send a task to Claude Code
/session - Check session status""")
            else:
                send_telegram_message("❌ Failed to start session. Check logs for details")

    elif cmd == '/stop_claude':
        try:
            subprocess.run(['tmux', 'kill-session', '-t', TMUX_SESSION], check=True)
            send_telegram_message("✅ Claude Code session stopped")
        except subprocess.CalledProcessError:
            send_telegram_message("❌ Session does not exist or failed to stop")
        except Exception as e:
            send_telegram_message(f"❌ Error: {e}")

    elif cmd == '/status':
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

*Interactive Session:*
/ask <task> - Send task to Claude Code (auto-starts session)
/session - Check session status
/start_claude - Manually start Claude Code session
/stop_claude - Stop Claude Code session

*Monitoring:*
/status - Current tmux output
/last_output - Full last response

*Other:*
/help - This message
/claude <cmd> - Execute command in tmux

*Example:*
/ask Analyze the webhook_server.py file"""
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
