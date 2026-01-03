"""
Telegram 命令处理模块

处理来自 Telegram 的各种命令
"""

import logging
import subprocess
from .telegram_api import send_telegram_message
from .claude_tmux import get_current_tmux_session, send_task_to_claude
from .history import get_history
from .state import get_last_outputs

logger = logging.getLogger(__name__)


def handle_command(command):
    """执行来自 Telegram 的命令"""
    cmd = command.lower().strip()

    if cmd == '/current':
        handle_current_command()
    elif cmd == '/status':
        handle_status_command()
    elif cmd == '/last_output':
        handle_last_output_command()
    elif cmd == '/last':
        handle_last_command()
    elif cmd.startswith('/history'):
        handle_history_command(command)
    elif cmd == '/help':
        handle_help_command()
    elif cmd.startswith('/claude '):
        handle_claude_command(command)
    elif cmd == '/sessions':
        handle_sessions_command()
    elif cmd.startswith('/switch '):
        handle_switch_command(command)
    else:
        send_telegram_message("<b>※ Unknown Command</b>\\n\\n")


def handle_current_command():
    """显示当前会话信息"""
    tmux_session = get_current_tmux_session()
    msg = f"这是你当前的会话哦~ (｡･ω･｡)\n\n<b>{tmux_session}</b>\n\n※ 使用 /help 查看命令"
    send_telegram_message(msg)


def handle_status_command():
    """获取最近的 tmux 输出"""
    try:
        tmux_session = get_current_tmux_session()
        output = subprocess.check_output(
            ['tmux', 'capture-pane', '-t', tmux_session, '-p'],
            text=True
        )
        last_lines = '\\n'.join(output.split('\\n')[-10:])
        send_telegram_message(f"""<b>Status</b>

<code>{last_lines}</code>

<a href="/help">/help</a>""")
    except Exception:
        send_telegram_message("<b>※ Status Unavailable</b>\\n\\n")


def handle_last_output_command():
    """发送最后存储的输出"""
    last_outputs = get_last_outputs()
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


def handle_last_command():
    """获取最后的历史记录条目（任何类型）"""
    history = get_history(limit=1)
    if history:
        entry = history[0]
        timestamp = entry['timestamp'].split('T')[1][:5]
        event_type = entry['event_type']
        preview = entry['message'][:300]

        msg = f"""<b>Last Event</b>

<code>{timestamp}</code>  {event_type}

{preview}

<a href="/help">/help</a>"""
        send_telegram_message(msg)
    else:
        send_telegram_message("<b>History Empty</b>\\n\\n")


def handle_history_command(command):
    """处理 /history 命令"""
    parts = command.split()
    limit = 10
    event_type = None

    # 解析参数
    if len(parts) > 1:
        try:
            limit = int(parts[1])
            limit = min(limit, 50)
        except ValueError:
            event_type = parts[1]

    if len(parts) > 2:
        event_type = parts[2]

    # 获取历史记录
    history = get_history(limit=limit, event_type=event_type)

    if not history:
        msg = "<b>History Empty</b>"
        if event_type:
            msg += f"\\n\\nType: <code>{event_type}</code>"
        send_telegram_message(f"{msg}\\n\\n")
        return

    # 格式化消息 - 显示最后 5 条
    msg = "<b>History</b>\\n\\n"
    for entry in reversed(history[-5:]):
        timestamp = entry['timestamp'].split('T')[1][:5]
        event = entry['event_type'][:10]
        preview = entry['message'][:35].replace('\\n', ' ')
        msg += f"<code>{timestamp}</code> {event}\\n{preview}...\\n\\n"

    msg += ""
    send_telegram_message(msg)


def handle_help_command():
    """显示帮助信息"""
    help_text = """我是你的专属 Claude 助手！(๑•̀ㅂ•́)و✧

下面是我能帮你做的事情：

/current - 查看当前会话信息
/sessions - 列出所有会话并切换
/status - 查看 Claude 最新输出
/last - 查看最后一次事件
/history [N] - 查看历史记录（可选数量）"""
    send_telegram_message(help_text, skip_help_link=True)


def handle_claude_command(command):
    """向 Claude Code tmux 会话发送命令"""
    actual_command = command[8:]  # 移除 '/claude '
    try:
        tmux_session = get_current_tmux_session()
        subprocess.run(
            ['tmux', 'send-keys', '-t', tmux_session, actual_command, 'C-m'],
            check=True
        )
        preview = actual_command[:50]
        send_telegram_message(
            f"<b>✓ Command Sent</b>\\n\\n<code>{preview}</code>\\n\\n"
            ""
        )
    except Exception:
        send_telegram_message("<b>※ Send Failed</b>\\n\\n")


def handle_sessions_command():
    """列出所有 tmux 会话"""
    try:
        result = subprocess.run(
            ['tmux', 'list-sessions', '-F', '#{session_name}'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            send_telegram_message("<b>※ No Sessions</b>\n\n")
            return

        sessions = [
            s.strip()
            for s in result.stdout.strip().split('\n')
            if s.strip()
        ]

        if not sessions:
            send_telegram_message("<b>※ No Sessions</b>\n\n")
            return

        current_session = get_current_tmux_session()
        msg = "<b>Select Session</b>\n\nClick to switch\n\n"

        keyboard = []
        for session in sessions:
            if session == 'webhook':
                continue
            is_current = session == current_session
            button_text = f"◉ {session}" if is_current else session
            keyboard.append([{
                'text': button_text,
                'callback_data': f"switch_session_{session}"
            }])

        reply_markup = {'inline_keyboard': keyboard}
        send_telegram_message(msg, reply_markup=reply_markup)

    except subprocess.TimeoutExpired:
        send_telegram_message("<b>※ Timeout</b>\n\n")
    except Exception as e:
        logger.error(f"Error listing tmux sessions: {e}")
        send_telegram_message("<b>※ Error</b>\n\n")


def handle_switch_command(command):
    """切换项目"""
    from .claude_tmux import switch_project

    project_id = command[8:].strip()

    if not project_id:
        send_telegram_message("<b>※ Missing ID</b>\\n\\n")
        return

    success, message = switch_project(project_id)

    if success:
        send_telegram_message(
            f"<b>✓ Switched</b>\\n\\n{message}\\n\\n"
            ""
        )
    else:
        send_telegram_message(
            f"<b>※ Failed</b>\\n\\n{message}\\n\\n"
            ""
        )
