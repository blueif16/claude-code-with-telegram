"""
健康检查模块

负责系统健康检查（Telegram API、Tmux 服务器等）
"""

import logging
import os
import subprocess
from .telegram_api import check_telegram_api, send_telegram_message

logger = logging.getLogger(__name__)


def check_tmux_server_status():
    """检查 tmux 服务器状态（用于健康端点）"""
    try:
        result = subprocess.run(
            ['tmux', 'list-sessions'],
            capture_output=True,
            text=True,
            timeout=2
        )

        if result.returncode == 0:
            session_count = len([
                l for l in result.stdout.strip().split('\n') if l
            ])
            return {
                'running': True,
                'sessions': session_count,
                'socket': f"/private/tmp/tmux-{os.getuid()}/default"
            }
        elif 'no server running' in result.stderr.lower():
            return {
                'running': False,
                'error': 'No server running'
            }
        else:
            return {
                'running': True,
                'sessions': 0
            }
    except Exception as e:
        return {
            'running': False,
            'error': str(e)
        }


def ensure_tmux_server():
    """确保 tmux 服务器运行，必要时启动"""
    try:
        # 通过列出会话检查 tmux 服务器是否运行
        result = subprocess.run(
            ['tmux', 'list-sessions'],
            capture_output=True,
            text=True
        )

        # 如果命令成功或失败但不是"no server running"消息，服务器正在运行
        if result.returncode == 0 or 'no server running' not in result.stderr.lower():
            logger.info("Tmux server is running")
            return True

        # 服务器未运行，尝试启动
        logger.warning("Tmux server not running, attempting to start...")

        # 创建并立即杀死一个虚拟会话以启动服务器
        subprocess.run(
            ['tmux', 'new-session', '-d', '-s', 'tmux-init-dummy'],
            check=True,
            capture_output=True
        )
        subprocess.run(
            ['tmux', 'kill-session', '-t', 'tmux-init-dummy'],
            check=False,
            capture_output=True
        )

        # 验证服务器现在正在运行
        result = subprocess.run(
            ['tmux', 'list-sessions'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 or 'no server running' not in result.stderr.lower():
            logger.info("✅ Tmux server started successfully")
            return True
        else:
            logger.error("❌ Failed to start tmux server")
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"Error starting tmux server: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error with tmux server: {e}")
        return False


def perform_startup_health_check():
    """在启动时执行全面的健康检查"""
    logger.info("=" * 60)
    logger.info("Starting comprehensive health check...")
    logger.info("=" * 60)

    health_status = {
        'tmux_server': None,
        'telegram_api': None,
        'overall': 'unknown'
    }

    # 检查 tmux 服务器
    logger.info("Checking tmux server...")
    if ensure_tmux_server():
        tmux_status = check_tmux_server_status()
        health_status['tmux_server'] = tmux_status
        if tmux_status.get('running'):
            logger.info(
                f"✅ Tmux server: OK ({tmux_status.get('sessions', 0)} sessions)"
            )
        else:
            logger.warning(
                f"⚠️  Tmux server: {tmux_status.get('error', 'Unknown error')}"
            )
    else:
        health_status['tmux_server'] = {
            'running': False, 'error': 'Failed to start'}
        logger.error("❌ Tmux server: FAILED")

    # 检查 Telegram API
    logger.info("Checking Telegram API connectivity...")
    telegram_status = check_telegram_api()
    health_status['telegram_api'] = telegram_status

    if telegram_status.get('reachable'):
        if telegram_status.get('test_mode'):
            logger.info("✅ Telegram API: TEST MODE")
        else:
            logger.info(
                f"✅ Telegram API: OK (@{telegram_status.get('bot_username')})"
            )
    else:
        logger.error(
            f"❌ Telegram API: {telegram_status.get('error', 'Unknown error')}"
        )

    # 确定整体状态
    tmux_ok = health_status['tmux_server'] and health_status['tmux_server'].get(
        'running')
    telegram_ok = health_status['telegram_api'] and health_status['telegram_api'].get(
        'reachable')

    if tmux_ok and telegram_ok:
        health_status['overall'] = 'healthy'
        logger.info("=" * 60)
        logger.info("✅ Health check PASSED - All systems operational")
        logger.info("=" * 60)
    elif tmux_ok or telegram_ok:
        health_status['overall'] = 'degraded'
        logger.warning("=" * 60)
        logger.warning("⚠️  Health check DEGRADED - Some systems have issues")
        logger.warning("=" * 60)

        # 如果 Telegram 工作，发送警报到 Telegram
        if telegram_ok:
            try:
                alert_msg = "⚠️ Webhook Server Health Alert\n\n"
                if not tmux_ok:
                    alert_msg += "❌ Tmux server: Not running\n"
                alert_msg += "\nServer started but some components need attention."
                send_telegram_message(alert_msg)
            except Exception as e:
                logger.error(f"Failed to send health alert: {e}")
    else:
        health_status['overall'] = 'unhealthy'
        logger.error("=" * 60)
        logger.error("❌ Health check FAILED - Critical systems down")
        logger.error("=" * 60)

    return health_status
