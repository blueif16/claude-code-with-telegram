#!/usr/bin/env python3
import json
import logging
import os
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
