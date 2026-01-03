"""
Claude/Tmux 交互模块

负责与 Claude Code tmux 会话的所有交互
"""

import logging
import os
import subprocess
import time
from .config import get_config, get_claude_config, get_projects_config

logger = logging.getLogger(__name__)

# 全局变量
_current_project = None
_tmux_session = None


def init_project_context():
    """初始化项目上下文"""
    global _current_project, _tmux_session

    projects_config = get_projects_config()
    _current_project = projects_config.get('current', 'default')

    # Session 名称（支持从配置读取或环境变量）
    _tmux_session = os.environ.get(
        'TEL_SESSION') or get_claude_config().get('session_name', 'main')


def get_current_project_config():
    """获取当前项目配置"""
    if _current_project is None:
        init_project_context()

    projects_config = get_projects_config()
    project_list = projects_config.get('list', {})

    if _current_project in project_list:
        return project_list[_current_project]
    return None


def get_current_tmux_session():
    """获取当前项目的 tmux 会话名"""
    if _tmux_session is None:
        init_project_context()

    project_config = get_current_project_config()
    if project_config:
        return project_config.get('tmux_session', _tmux_session)
    return _tmux_session


def switch_project(project_id):
    """切换到指定项目"""
    global _current_project

    projects_config = get_projects_config()
    project_list = projects_config.get('list', {})

    if project_id not in project_list:
        return False, f"项目 '{project_id}' 不存在"

    _current_project = project_id

    # 更新配置文件
    config = get_config()
    config['projects']['current'] = project_id
    from .config import save_config
    save_config(config)

    return True, f"已切换到项目: {project_list[project_id]['name']}"


def send_task_to_claude(task):
    """通过 tmux 向 Claude Code 发送任务"""
    try:
        tmux_session = get_current_tmux_session()
        logger.info(f"Sending task to Claude Code: {task[:50]}...")

        # 向 tmux 会话发送任务
        subprocess.run(
            ['tmux', 'send-keys', '-t', tmux_session, task, 'C-m'],
            check=True
        )

        # 等待文本输入
        time.sleep(0.5)

        # 再发送一个 Enter 来提交提示
        subprocess.run(
            ['tmux', 'send-keys', '-t', tmux_session, 'C-m'],
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
