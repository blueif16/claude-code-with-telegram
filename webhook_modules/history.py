"""
历史记录管理模块

负责事件历史的加载、保存和查询
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# 历史记录配置
MAX_HISTORY_ENTRIES = 100
_history_file = None


def get_history_file():
    """获取历史记录文件路径"""
    global _history_file

    if _history_file is not None:
        return _history_file

    # 确定日志目录
    if os.environ.get('TEL_CONFIG', '').startswith(str(Path.home())):
        # 使用主配置，日志放在 ~/.claude-telegram/logs
        log_dir = Path.home() / '.claude-telegram' / 'logs'
    else:
        # 使用项目配置，日志放在项目的 logs 目录
        log_dir = Path('logs')

    # 创建日志目录
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        # 如果不可写，使用临时目录
        import time
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        log_dir = Path(f'logs.{timestamp}')
        log_dir.mkdir(parents=True, exist_ok=True)

    _history_file = log_dir / 'history.json'
    return _history_file


def load_history():
    """从 JSON 文件加载历史记录"""
    try:
        history_file = get_history_file()
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Failed to load history: {e}")
        return []


def save_history(history):
    """保存历史记录到 JSON 文件"""
    try:
        history_file = get_history_file()
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save history: {e}")
        return False


def add_to_history(event_type, message, raw_data):
    """添加条目到历史记录（带大小限制）"""
    history = load_history()

    entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'message': message,
        'raw_data': raw_data
    }

    history.append(entry)

    # 只保留最后 MAX_HISTORY_ENTRIES 条
    if len(history) > MAX_HISTORY_ENTRIES:
        history = history[-MAX_HISTORY_ENTRIES:]

    save_history(history)
    return entry


def get_history(limit=10, event_type=None):
    """获取历史记录条目（可选过滤）"""
    history = load_history()

    # 按事件类型过滤（如果指定）
    if event_type:
        history = [h for h in history if h.get('event_type') == event_type]

    # 返回最后 N 条
    return history[-limit:] if limit else history
