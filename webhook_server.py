#!/usr/bin/env python3
"""
Webhook Server - Claude Code + Telegram 双向通信系统

简化的主文件，所有功能已模块化
"""

import os
from webhook_modules.state import get_uptime_string
from webhook_modules.health_check import perform_startup_health_check
from webhook_modules.routes import register_routes
from webhook_modules.config import load_config, get_config, get_webhook_config
import sys
import shutil
import logging
from pathlib import Path
from flask import Flask

# 检查必需的系统依赖


def check_dependencies():
    """检查是否安装了必需的系统依赖"""
    missing = []

    if not shutil.which('tmux'):
        missing.append('tmux')
    if not shutil.which('jq'):
        missing.append('jq')

    if missing:
        print(f"❌ 缺少依赖: {', '.join(missing)}")
        print(f"请运行: ./setup.sh")
        sys.exit(1)


check_dependencies()

# 导入所有模块

# 加载配置
config = load_config()

# 确定日志目录
if os.environ.get('TEL_CONFIG', '').startswith(str(Path.home())):
    LOG_DIR = Path.home() / '.claude-telegram' / 'logs'
else:
    LOG_DIR = Path('logs')

# 创建日志目录
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    test_file = LOG_DIR / '.write_test'
    test_file.touch()
    test_file.unlink()
except (PermissionError, OSError) as e:
    import time
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    LOG_DIR = Path(f'logs.{timestamp}')
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"⚠️  原日志目录不可写，使用临时目录: {LOG_DIR}")

# 配置日志
log_handlers = [logging.StreamHandler()]
try:
    log_handlers.append(logging.FileHandler(LOG_DIR / 'webhook.log'))
except (PermissionError, OSError):
    print(f"⚠️  无法创建日志文件，仅使用控制台输出")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# Test mode
TEST_MODE = os.environ.get('TEST_MODE', '0') == '1'
if TEST_MODE:
    logger.info("🧪 TEST MODE ENABLED - Telegram API calls will be simulated")

# 创建 Flask 应用
app = Flask(__name__)

# 注册所有路由
register_routes(app)

if __name__ == '__main__':
    # 获取服务器配置
    webhook_config = get_webhook_config()
    server_host = webhook_config.get('host', '127.0.0.1')
    server_port = int(
        os.environ.get(
            'TEL_PORT',
            webhook_config.get(
                'port',
                8000)))

    # 获取会话名称
    claude_config = config.get('claude', {})
    tmux_session = os.environ.get(
        'TEL_SESSION') or claude_config.get('session_name', 'main')

    logger.info(f"Starting webhook server on {server_host}:{server_port}...")
    logger.info(f"Tmux session: {tmux_session}")

    # 执行全面的健康检查
    health_status = perform_startup_health_check()

    # 无论健康检查结果如何都启动服务器（降级模式可接受）
    app.run(host=server_host, port=server_port, debug=False)
