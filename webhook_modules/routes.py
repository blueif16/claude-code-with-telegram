"""
Flask 路由处理模块

定义所有 Flask 路由和请求处理
"""

import logging
import subprocess
from datetime import datetime
from flask import request, jsonify
from .telegram_api import send_telegram_message, answer_callback_query
from .claude_tmux import get_current_tmux_session, send_task_to_claude
from .question_handler import handle_question_prompt, get_pending_questions
from .history import add_to_history
from .notification import should_notify
from .commands import handle_command
from .state import get_last_outputs, set_last_output, get_uptime_string
from .health_check import check_tmux_server_status, check_telegram_api
from .config import get_telegram_config, get_config, save_config

logger = logging.getLogger(__name__)


def register_routes(app):
    """注册所有 Flask 路由"""

    @app.route('/claude-hook', methods=['POST'])
    def claude_hook():
        """接收来自 Claude Code hooks 的通知"""
        try:
            data = request.get_json()
            event = data.get('event', 'unknown')
            message = data.get('message', 'No message')
            raw_data = data.get('raw_data', {})
            is_question = data.get('is_question', False)
            questions = data.get('questions', [])

            logger.info(
                f"Received Claude hook: {event}, is_question={is_question}, questions_count={len(questions)}")

            # 存储最后输出以供检索
            set_last_output(event, {'raw_data': raw_data, 'message': message})

            # 添加到持久化历史记录
            add_to_history(event, message, raw_data)

            # 特殊处理问题
            if is_question and questions:
                handle_question_prompt(questions, raw_data)
            elif should_notify(event, raw_data):
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
        """接收来自 Telegram 的命令"""
        # 验证 secret token
        telegram_config = get_telegram_config()
        secret_token = telegram_config.get('secret_token')
        token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')

        if token != secret_token:
            logger.warning(f"Invalid token from {request.remote_addr}")
            return jsonify({'error': 'Invalid token'}), 403

        try:
            data = request.get_json()

            # 处理回调查询（按钮点击）
            if 'callback_query' in data:
                handle_callback_query(data['callback_query'])
                return jsonify({'ok': True}), 200

            # 处理常规消息
            message = data.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')

            # 验证 chat_id
            expected_chat_id = telegram_config.get('chat_id')
            if str(chat_id) != str(expected_chat_id):
                logger.warning(f"Unauthorized chat_id: {chat_id}")
                return jsonify({'ok': False}), 403

            logger.info(f"Received message: {text}")

            # 处理命令和消息
            if text.startswith('/'):
                # 命令
                handle_command(text)
            else:
                # 常规消息 - 发送到 Claude Code
                handle_message_to_claude(text)

            return jsonify({'ok': True}), 200

        except Exception as e:
            logger.error(f"Error in telegram_webhook: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/health', methods=['GET'])
    def health():
        """健康检查端点"""
        tmux_status = check_tmux_server_status()
        telegram_status = check_telegram_api()

        last_outputs = get_last_outputs()

        return jsonify({
            'status': 'ok',
            'timestamp': datetime.now().isoformat(),
            'uptime': get_uptime_string(),
            'tmux_server': tmux_status,
            'telegram_api': telegram_status,
            'last_outputs': {k: v is not None for k, v in last_outputs.items()}
        }), 200


def handle_message_to_claude(message):
    """处理常规消息 - 发送到当前 tmux 会话"""
    try:
        if not message or not message.strip():
            return

        # 获取当前会话并发送消息
        tmux_session = get_current_tmux_session()

        if send_task_to_claude(message):
            preview = message[:50] if len(
                message) <= 50 else message[:47] + "..."
            msg = f"""<b>✓ Sent to Claude</b>

{preview}"""
            send_telegram_message(msg)
            logger.info(f"Message sent to tmux session: {tmux_session}")
        else:
            send_telegram_message(
                "<b>※ Send Failed</b>\\n\\n"
                f"Check session: <code>{tmux_session}</code>"
            )

    except Exception as e:
        logger.error(f"Error handling message to Claude: {e}")
        send_telegram_message(
            f"<b>※ Error</b>\\n\\n{str(e)[:100]}"
        )


def handle_callback_query(callback_query):
    """处理按钮点击（内联键盘）"""
    try:
        callback_id = callback_query.get('id')
        callback_data = callback_query.get('data', '')

        logger.info(f"Received callback: {callback_data}")

        # 处理会话切换: switch_session_{session_name}
        if callback_data.startswith('switch_session_'):
            handle_session_switch(callback_id, callback_data)
            return

        # 处理问题回答: ans_{question_id}_{option_index}
        if callback_data.startswith('ans_'):
            handle_answer_callback(callback_id, callback_data)
            return

    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        try:
            answer_callback_query(callback_id, f"❌ 错误: {str(e)[:50]}")
        except BaseException:
            pass


def handle_session_switch(callback_id, callback_data):
    """处理会话切换回调"""
    session_name = callback_data[15:]  # 移除 'switch_session_' 前缀

    try:
        # 检查会话是否存在
        result = subprocess.run(
            ['tmux', 'has-session', '-t', session_name],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            answer_callback_query(callback_id, f"❌ 会话 '{session_name}' 不存在")
            return

        # 更新配置中的当前 tmux 会话
        config = get_config()
        projects_config = config.get('projects', {})
        project_list = projects_config.get('list', {})

        # 查找匹配的项目或更新默认值
        project_found = False
        for project_id, project_info in project_list.items():
            if project_info.get('tmux_session') == session_name:
                # 切换到此项目
                config['projects']['current'] = project_id
                project_found = True
                break

        if not project_found:
            # 更新默认 tmux 会话
            if 'claude' not in config:
                config['claude'] = {}
            config['claude']['session_name'] = session_name

        # 保存配置
        save_config(config)

        answer_callback_query(callback_id, f"✓ 已切换到: {session_name}")

        # 发送确认消息
        msg = f"✓ 已切换到会话: {session_name}\\n\\n"
        msg += "现在可以使用:\\n"
        msg += "• /ask <任务> → 发送任务到此会话\\n"
        msg += "• /status → 查看会话状态\\n"
        msg += "• /current → 查看会话详情"
        send_telegram_message(msg)

        logger.info(f"Switched to tmux session: {session_name}")

    except Exception as e:
        logger.error(f"Failed to switch session: {e}")
        answer_callback_query(callback_id, f"❌ 切换失败: {str(e)[:30]}")


def handle_answer_callback(callback_id, callback_data):
    """处理问题回答回调"""
    parts = callback_data.split('_')
    if len(parts) < 3:
        answer_callback_query(callback_id, "❌ 无效的回调数据")
        return

    question_id = parts[1]
    option_index = parts[2]

    # 检索问题数据
    pending_questions = get_pending_questions()
    if question_id not in pending_questions:
        answer_callback_query(callback_id, "❌ 问题已过期")
        return

    question_data = pending_questions[question_id]
    questions = question_data['questions']

    if not questions:
        answer_callback_query(callback_id, "❌ 无效的问题")
        return

    first_q = questions[0]
    options = first_q.get('options', [])

    # 处理"其他"选项
    if option_index == 'other':
        answer_callback_query(callback_id, "请直接发送文本回复")
        send_telegram_message("请输入你的回答:")
        return

    # 获取选中的选项
    try:
        idx = int(option_index)
        if idx < 0 or idx >= len(options):
            answer_callback_query(callback_id, "❌ 无效选项")
            return

        selected_option = options[idx]
        answer_text = selected_option.get('label', f'选项{idx+1}')

        # 向 Claude Code 发送答案（单个 Enter，不像 send_task_to_claude 那样双 Enter）
        try:
            tmux_session = get_current_tmux_session()
            subprocess.run(['tmux', 'send-keys', '-t',
                           tmux_session, answer_text, 'C-m'], check=True)

            answer_callback_query(callback_id, f"✓ 已选择: {answer_text}")
            send_telegram_message(f"✓ 已发送回答: {answer_text}")
            logger.info(f"Answer sent to Claude Code: {answer_text}")

            # 清理
            del pending_questions[question_id]
        except Exception as e:
            logger.error(f"Failed to send answer: {e}")
            answer_callback_query(callback_id, "❌ 发送失败")

    except ValueError:
        answer_callback_query(callback_id, "❌ 无效的选项索引")
