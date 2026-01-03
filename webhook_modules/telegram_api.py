"""
Telegram API 交互模块

负责与 Telegram Bot API 的所有交互
"""

import logging
import os
import requests
from .config import get_telegram_config

logger = logging.getLogger(__name__)

# Test mode - set TEST_MODE=1 to disable Telegram API calls
TEST_MODE = os.environ.get('TEST_MODE', '0') == '1'


def send_telegram_message(
        text,
        parse_mode='HTML',
        reply_markup=None,
        skip_help_link=False):
    """发送消息到 Telegram

    Args:
        text: 消息文本
        parse_mode: HTML 或 Markdown
        reply_markup: 内联键盘标记
        skip_help_link: 如果为 True，不添加 /help 链接（用于 /help 命令本身）
    """
    # 为所有消息添加 /help 链接（除了 /help 命令本身）
    if not skip_help_link and '※ 使用 /help 查看命令' not in text:
        text = f"{text}\n※ 使用 /help 查看命令"

    if TEST_MODE:
        logger.info(f"📤 [TEST MODE] Would send to Telegram:\n{text}")
        if reply_markup:
            logger.info(f"📤 [TEST MODE] With reply_markup: {reply_markup}")
        return {'ok': True, 'result': {'message_id': 'test_mode'}}

    telegram_config = get_telegram_config()
    bot_token = telegram_config.get('bot_token')
    chat_id = telegram_config.get('chat_id')

    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'

    payload = {
        'chat_id': chat_id,
        'text': text,
        'disable_web_page_preview': True
    }

    if parse_mode:
        payload['parse_mode'] = parse_mode

    if reply_markup:
        payload['reply_markup'] = reply_markup

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(
            f"Telegram message sent: {response.json().get('result', {}).get('message_id')}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        raise


def answer_callback_query(callback_id, text):
    """回答回调查询（向用户显示弹窗）"""
    if TEST_MODE:
        logger.info(f"📤 [TEST MODE] Would answer callback: {text}")
        return

    telegram_config = get_telegram_config()
    bot_token = telegram_config.get('bot_token')

    url = f'https://api.telegram.org/bot{bot_token}/answerCallbackQuery'
    payload = {
        'callback_query_id': callback_id,
        'text': text
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f"Callback answered: {text}")
    except Exception as e:
        logger.error(f"Failed to answer callback: {e}")


def check_telegram_api():
    """检查 Telegram API 连接性"""
    if TEST_MODE:
        return {
            'reachable': True,
            'test_mode': True
        }

    try:
        telegram_config = get_telegram_config()
        bot_token = telegram_config.get('bot_token')

        url = f'https://api.telegram.org/bot{bot_token}/getMe'
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
