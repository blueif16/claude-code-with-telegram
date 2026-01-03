"""
全局状态管理模块

管理 webhook 服务器的全局状态变量
"""

from datetime import datetime

# 存储最后的输出（简单的内存存储）
last_outputs = {
    'stop': None,
    'tool_use': None,
    'subagent': None
}

# 服务器启动时间（用于 uptime 跟踪）
server_start_time = datetime.now()


def get_last_outputs():
    """获取最后输出的字典"""
    return last_outputs


def set_last_output(event_type, data):
    """设置特定事件类型的最后输出"""
    if event_type in last_outputs:
        last_outputs[event_type] = {
            'timestamp': datetime.now().isoformat(),
            'data': data.get('raw_data', {}),
            'message': data.get('message', '')
        }


def get_server_start_time():
    """获取服务器启动时间"""
    return server_start_time


def get_uptime_seconds():
    """获取服务器运行时间（秒）"""
    return (datetime.now() - server_start_time).total_seconds()


def get_uptime_string():
    """获取服务器运行时间（格式化字符串）"""
    uptime_seconds = get_uptime_seconds()
    hours = int(uptime_seconds // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    return f"{hours}h {minutes}m"
