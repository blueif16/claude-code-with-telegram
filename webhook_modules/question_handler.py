"""
AskUserQuestion 处理模块

负责处理 Claude Code 的 AskUserQuestion 提示
"""

import logging
import time
from datetime import datetime
from .telegram_api import send_telegram_message

logger = logging.getLogger(__name__)

# 存储待处理的问题（等待用户响应）
pending_questions = {}


def get_pending_questions():
    """获取待处理的问题字典"""
    return pending_questions


def handle_question_prompt(questions, raw_data):
    """处理 AskUserQuestion 提示（带内联键盘）"""
    try:
        # 生成唯一的问题 ID
        question_id = str(int(time.time() * 1000))

        # 存储问题数据以便后续检索
        pending_questions[question_id] = {
            'questions': questions,
            'raw_data': raw_data,
            'timestamp': datetime.now().isoformat()
        }

        # 格式化消息（包含所有问题）
        msg = "【Claude 需要你的回答】\n\n"

        for i, q in enumerate(questions, 1):
            question_text = q.get('question', '无问题')
            header = q.get('header', '')
            multi_select = q.get('multiSelect', False)

            msg += f"{i}. {question_text}\n"
            if header:
                msg += f"   标签: {header}\n"
            if multi_select:
                msg += "   (可多选)\n"

            # 列出选项
            options = q.get('options', [])
            for j, opt in enumerate(options, 1):
                label = opt.get('label', f'选项{j}')
                desc = opt.get('description', '')
                msg += f"   {chr(96+j)}) {label}"
                if desc:
                    msg += f" - {desc[:50]}"
                msg += "\n"
            msg += "\n"

        # 创建内联键盘（简化版：目前只处理第一个问题）
        if questions:
            first_q = questions[0]
            options = first_q.get('options', [])

            keyboard = []
            for i, opt in enumerate(options):
                label = opt.get('label', f'选项{i+1}')
                callback_data = f"ans_{question_id}_{i}"
                keyboard.append(
                    [{'text': label, 'callback_data': callback_data}])

            # 添加"其他"选项
            keyboard.append([{
                'text': '其他 (输入文本)',
                'callback_data': f"ans_{question_id}_other"
            }])

            reply_markup = {'inline_keyboard': keyboard}

            send_telegram_message(msg, reply_markup=reply_markup)
            logger.info(f"✓ Question prompt sent with {len(options)} options")
        else:
            send_telegram_message(msg)

    except Exception as e:
        logger.error(f"Error handling question prompt: {e}")
        send_telegram_message(f"❌ 处理问题时出错: {e}")
