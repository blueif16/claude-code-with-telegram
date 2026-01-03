"""
配置管理模块

负责配置文件的查找、加载和管理
"""

import json
import os
import sys
from pathlib import Path

# 全局配置存储
_config = None
_config_file = None


def find_config_file():
    """查找配置文件（优先级：环境变量 > 本地 > 全局）"""
    # 1. 环境变量指定
    if 'TEL_CONFIG' in os.environ:
        config_path = os.environ['TEL_CONFIG']
        if os.path.exists(config_path):
            return config_path

    # 2. 本地项目配置
    local_config = '.claude-telegram/config.json'
    if os.path.exists(local_config):
        return local_config

    # 3. 全局配置
    global_config = os.path.expanduser('~/.claude-telegram/config.json')
    if os.path.exists(global_config):
        return global_config

    # 4. 兼容旧配置
    if os.path.exists('config.json'):
        return 'config.json'

    print("❌ 配置文件未找到")
    print("请创建以下任一配置文件:")
    print("  • .claude-telegram/config.json (项目配置)")
    print("  • ~/.claude-telegram/config.json (主配置)")
    sys.exit(1)


def load_config():
    """加载配置文件"""
    global _config, _config_file

    _config_file = find_config_file()
    print(f"📝 使用配置: {_config_file}")

    with open(_config_file, 'r', encoding='utf-8') as f:
        _config = json.load(f)

    return _config


def get_config():
    """获取当前配置"""
    if _config is None:
        load_config()
    return _config


def get_config_file():
    """获取配置文件路径"""
    if _config_file is None:
        find_config_file()
    return _config_file


def save_config(config=None):
    """保存配置到文件"""
    global _config
    if config is not None:
        _config = config

    if _config_file is None:
        raise RuntimeError("配置文件路径未初始化")

    with open(_config_file, 'w', encoding='utf-8') as f:
        json.dump(_config, f, indent=2, ensure_ascii=False)


def get_telegram_config():
    """获取 Telegram 配置"""
    config = get_config()
    return config.get('telegram', {})


def get_webhook_config():
    """获取 Webhook 配置"""
    config = get_config()
    return config.get('webhook', {})


def get_claude_config():
    """获取 Claude 配置"""
    config = get_config()
    return config.get('claude', {})


def get_projects_config():
    """获取项目配置"""
    config = get_config()
    return config.get('projects', {})


def get_notification_config():
    """获取通知配置"""
    config = get_config()
    return config.get('notification', {})
