#!/usr/bin/env python3
"""
验证 AskUserQuestion 端到端流程
"""
import json
import subprocess
import time

print("🧪 验证 AskUserQuestion 功能")
print("=" * 60)

# 1. 检查 webhook 服务器状态
print("\n1. 检查 webhook 服务器...")
result = subprocess.run(['curl', '-s', 'http://localhost:8000/health'], capture_output=True, text=True)
if result.returncode == 0:
    health = json.loads(result.stdout)
    if health['status'] == 'ok':
        print("   ✅ Webhook 服务器运行正常")
    else:
        print("   ❌ Webhook 服务器状态异常")
        exit(1)
else:
    print("   ❌ 无法连接到 webhook 服务器")
    exit(1)

# 2. 运行测试
print("\n2. 运行 AskUserQuestion 测试...")
result = subprocess.run(['./test_question_flow.sh'], capture_output=True, text=True)
if result.returncode == 0:
    print("   ✅ 测试脚本执行成功")
else:
    print(f"   ❌ 测试脚本失败: {result.stderr}")
    exit(1)

# 3. 检查 webhook 日志
print("\n3. 检查 webhook 日志...")
with open('logs/webhook.log', 'rb') as f:
    lines = f.readlines()

found_question = False
found_keyboard = False

for line in lines[-50:]:
    try:
        decoded = line.decode('utf-8', errors='ignore')
        if 'is_question=True' in decoded:
            found_question = True
            print("   ✅ 检测到 is_question=True")
        if 'Question prompt sent' in decoded:
            found_keyboard = True
            print("   ✅ 检测到内联键盘已发送")
    except:
        pass

if not found_question:
    print("   ❌ 未检测到 is_question=True")
    exit(1)

if not found_keyboard:
    print("   ❌ 未检测到内联键盘发送")
    exit(1)

# 4. 检查历史记录
print("\n4. 检查历史记录...")
with open('logs/history.json', 'r') as f:
    history = json.load(f)

notifications = [h for h in history if h['event_type'] == 'notification']
if notifications:
    last_notif = notifications[-1]
    if last_notif['raw_data'].get('notification_type') == 'idle_prompt':
        print("   ✅ 历史记录中有 idle_prompt 事件")
    else:
        print(f"   ⚠️  最后的 notification 类型不是 idle_prompt: {last_notif['raw_data'].get('notification_type')}")
else:
    print("   ❌ 历史记录中没有 notification 事件")
    exit(1)

# 5. 总结
print("\n" + "=" * 60)
print("🎉 验证完成!")
print("\n✅ AskUserQuestion 功能正常工作:")
print("   • Hook 脚本正确提取 questions")
print("   • Webhook 服务器正确处理 is_question=True")
print("   • 内联键盘成功发送到 Telegram")
print("\n📱 请检查 Telegram 机器人,应该收到带按钮的消息")
print("=" * 60)
