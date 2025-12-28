#!/usr/bin/env python3
"""
轻量级子 Webhook 服务器
每个 tmux 会话运行一个实例，负责与该会话中的 Claude Code 交互
"""
import json
import logging
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify

# 从命令行参数获取配置
if len(sys.argv) < 3:
    print("用法: python3 sub_webhook_server.py <port> <tmux_session>")
    sys.exit(1)

PORT = int(sys.argv[1])
TMUX_SESSION = sys.argv[2]

# 设置日志
app = Flask(__name__)
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f'logs/sub_webhook_{TMUX_SESSION}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 服务器启动时间
server_start_time = datetime.now()

def check_tmux_session():
    """检查 tmux 会话是否存在"""
    try:
        result = subprocess.run(
            ['tmux', 'has-session', '-t', TMUX_SESSION],
            capture_output=True
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking tmux session: {e}")
        return False

def send_to_claude(text):
    """发送文本到 Claude Code（双回车提交）"""
    try:
        # 发送文本
        subprocess.run(
            ['tmux', 'send-keys', '-t', TMUX_SESSION, text, 'C-m'],
            check=True
        )
        # 等待一下
        import time
        time.sleep(0.5)
        # 再发送一次回车提交
        subprocess.run(
            ['tmux', 'send-keys', '-t', TMUX_SESSION, 'C-m'],
            check=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send to Claude: {e}")
        return False

def send_answer_to_claude(text):
    """发送回答到 Claude Code（单回车）"""
    try:
        subprocess.run(
            ['tmux', 'send-keys', '-t', TMUX_SESSION, text, 'C-m'],
            check=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send answer: {e}")
        return False

def capture_tmux_output(lines=20):
    """捕获 tmux 输出"""
    try:
        output = subprocess.check_output(
            ['tmux', 'capture-pane', '-t', TMUX_SESSION, '-p'],
            text=True
        )
        return '\n'.join(output.split('\n')[-lines:])
    except Exception as e:
        logger.error(f"Failed to capture output: {e}")
        return None

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    session_active = check_tmux_session()
    uptime_seconds = (datetime.now() - server_start_time).total_seconds()

    return jsonify({
        'status': 'ok',
        'port': PORT,
        'tmux_session': TMUX_SESSION,
        'session_active': session_active,
        'uptime_seconds': int(uptime_seconds)
    }), 200

@app.route('/ask', methods=['POST'])
def ask():
    """接收任务并发送到 Claude Code"""
    try:
        data = request.get_json()
        task = data.get('task', '')

        if not task:
            return jsonify({'error': 'No task provided'}), 400

        if not check_tmux_session():
            return jsonify({'error': f'Tmux session {TMUX_SESSION} not found'}), 404

        logger.info(f"Received task: {task[:50]}...")

        if send_to_claude(task):
            return jsonify({
                'ok': True,
                'message': f'Task sent to {TMUX_SESSION}'
            }), 200
        else:
            return jsonify({'error': 'Failed to send task'}), 500

    except Exception as e:
        logger.error(f"Error in /ask: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/answer', methods=['POST'])
def answer():
    """发送回答到 Claude Code（用于 AskUserQuestion）"""
    try:
        data = request.get_json()
        answer_text = data.get('answer', '')

        if not answer_text:
            return jsonify({'error': 'No answer provided'}), 400

        if not check_tmux_session():
            return jsonify({'error': f'Tmux session {TMUX_SESSION} not found'}), 404

        logger.info(f"Sending answer: {answer_text}")

        if send_answer_to_claude(answer_text):
            return jsonify({
                'ok': True,
                'message': f'Answer sent to {TMUX_SESSION}'
            }), 200
        else:
            return jsonify({'error': 'Failed to send answer'}), 500

    except Exception as e:
        logger.error(f"Error in /answer: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    """获取当前状态"""
    try:
        if not check_tmux_session():
            return jsonify({'error': f'Tmux session {TMUX_SESSION} not found'}), 404

        output = capture_tmux_output(20)

        return jsonify({
            'ok': True,
            'tmux_session': TMUX_SESSION,
            'output': output
        }), 200

    except Exception as e:
        logger.error(f"Error in /status: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Starting sub webhook server for {TMUX_SESSION} on port {PORT}")

    # 检查 tmux 会话
    if not check_tmux_session():
        logger.warning(f"⚠️  Tmux session '{TMUX_SESSION}' not found")
    else:
        logger.info(f"✓ Tmux session '{TMUX_SESSION}' is active")

    app.run(host='127.0.0.1', port=PORT, debug=False)
