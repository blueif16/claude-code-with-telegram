"""
通知过滤模块

智能决定是否发送通知到 Telegram
"""

import logging
from .config import get_notification_config

logger = logging.getLogger(__name__)


def should_notify(event, raw_data):
    """智能过滤：决定是否发送通知到 Telegram"""
    notification_config = get_notification_config()
    level = notification_config.get('level', 'normal')
    always_notify = notification_config.get(
        'always_notify_events',
        ['stop', 'error', 'permission', 'question']
    )
    silent_tools = notification_config.get(
        'silent_tools',
        ['Read', 'Grep', 'Glob', 'Edit', 'Write', 'Bash', 'Task']
    )
    silent_events = notification_config.get('silent_events', [])

    # 总是通知的重要事件
    if event in always_notify:
        return True

    # 检查是否在静默事件列表中
    if event in silent_events:
        logger.info(f"Silencing event: {event}")
        return False

    # tool_use 事件：检查工具是否在静默列表中
    if event == 'tool_use':
        tool_name = raw_data.get('tool_name', '')
        if tool_name in silent_tools:
            logger.info(f"Silencing tool: {tool_name}")
            return False
        return True

    # subagent 事件：根据 level 决定
    if event == 'subagent':
        if level == 'minimal':
            return False
        return True

    # 其他事件：根据 level 决定
    if level == 'minimal':
        return False

    return True
