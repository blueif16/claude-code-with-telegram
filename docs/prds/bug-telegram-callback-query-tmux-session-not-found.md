# Bug: Telegram Callback Query 无法传递到 Claude Code - Tmux Session 不存在

## 问题描述

当用户在 Telegram 中点击 AskUserQuestion 生成的按钮时，webhook 服务器成功接收到 callback_query，但在尝试通过 tmux 将答案发送到 Claude Code 时失败，错误信息为：

```
Failed to send task: Command '['tmux', 'send-keys', '-t', 'claude', '测试成功', 'C-m']' returned non-zero exit status 1.
```

导致 Telegram 显示"发送失败"，用户无法通过 Telegram 按钮回答问题。

## 背景

### 之前的配置
- 使用 Cloudflare webhook: `https://webhook.blueif.me/telegram-webhook`
- 该 webhook 在某个时间点开始返回 530 错误
- Telegram 有 10 个待处理的更新（pending_update_count: 10）
- 最后错误时间：1766863832

### 相关工作
- PRD: `docs/prds/bug-notification-hook-not-capturing-askuserquestion.md`
- 该文档记录了 PreToolUse hook 的问题和修复
- PreToolUse hook 现已正常工作，能够捕获 AskUserQuestion 调用

## 已完成的工作

### 1. 修复 callback_query 处理逻辑

**文件**: `webhook_server.py:741-754`

**问题**:
- 原代码调用 `send_task_to_claude()` 函数
- 该函数会发送两次 Enter（第一次发送文本+Enter，第二次再发送Enter）
- 设计用于多行任务提交，但不适合 AskUserQuestion 的单行答案

**修复**:
```python
# 旧代码
if send_task_to_claude(answer_text):
    answer_callback_query(callback_id, f"✓ 已选择: {answer_text}")
    ...

# 新代码
try:
    tmux_session = get_current_tmux_session()
    subprocess.run(['tmux', 'send-keys', '-t', tmux_session, answer_text, 'C-m'], check=True)
    answer_callback_query(callback_id, f"✓ 已选择: {answer_text}")
    ...
```

**状态**: ✅ 代码修复完成，逻辑正确

### 2. 配置公网隧道

**尝试方案**: ngrok
- 安装成功：`brew install ngrok`
- 启动失败：需要 authtoken
- 错误：`ERR_NGROK_4018 - authentication failed`
- 未配置账号和 authtoken

**采用方案**: localtunnel
- 安装：`npm install -g localtunnel`
- 启动：`lt --port 8000`
- 公网 URL：`https://fast-grapes-crash.loca.lt`
- 状态：✅ 隧道运行正常

### 3. 设置 Telegram webhook

**删除旧配置**:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook?drop_pending_updates=false"
```

**设置新配置**:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://fast-grapes-crash.loca.lt/telegram-webhook" \
  -d "secret_token=<SECRET>"
```

**验证结果**:
```json
{
  "url": "https://fast-grapes-crash.loca.lt/telegram-webhook",
  "pending_update_count": 0,
  "max_connections": 40,
  "ip_address": "193.34.76.44"
}
```

**状态**: ✅ Webhook 设置成功，无待处理更新

### 4. 验证 callback_query 接收

**Webhook 日志**:
```
2025-12-27 14:18:56,923 [INFO] Received callback: ans_1766873911205_0
2025-12-27 14:18:56,924 [INFO] Sending task to Claude Code: 测试成功...
```

**数据格式**: `ans_{question_id}_{option_index}`
- question_id: 时间戳（毫秒）
- option_index: 选项索引（0-based）

**状态**: ✅ Webhook 成功接收并解析 callback_query

## 当前问题

### 核心问题：Tmux Session 不存在

**错误信息**:
```
2025-12-27 14:18:56,938 [ERROR] Failed to send task: Command '['tmux', 'send-keys', '-t', 'claude', '测试成功', 'C-m']' returned non-zero exit status 1.
2025-12-27 14:18:57,727 [INFO] Callback answered: ❌ 发送失败
```

**原因分析**:
- `config.json` 配置的 `tmux_session` 是 "claude"
- 但系统中不存在名为 "claude" 的 tmux session
- `tmux send-keys -t claude` 命令失败，返回 exit code 1

**当前环境状态**:
- Claude Code 进程 PID: 97973
- 运行在 terminal: s039
- **不在 tmux 中运行**

**现有 tmux sessions**:
```
p0-smart-filter: 1 windows (created Fri Dec 26 18:23:43 2025)
p1-history-query: 1 windows (created Fri Dec 26 19:39:23 2025)
p2-multi-project: 1 windows (created Fri Dec 26 19:39:47 2025)
section-1-tmux-fix: 1 windows (created Fri Dec 26 14:08:18 2025)
section-2-hook-retry: 1 windows (created Fri Dec 26 14:08:35 2025)
section-3-health-check: 1 windows (created Fri Dec 26 14:08:38 2025)
```

**影响**:
- Telegram 按钮点击后显示"发送失败"
- 用户无法通过 Telegram 远程回答 AskUserQuestion
- 必须在本地终端手动输入答案

**状态**: ❌ 阻塞完整测试流程

## 解决方案

### 方案A：在 tmux 中运行 Claude Code（推荐）

**步骤**:
1. 创建名为 "claude" 的 tmux session
   ```bash
   tmux new-session -d -s claude
   ```

2. 在该 session 中启动 Claude Code
   ```bash
   tmux send-keys -t claude "cd /Users/tk/Desktop/claude-code-with-telegram" C-m
   tmux send-keys -t claude "claude" C-m
   ```

3. 重新测试 AskUserQuestion 流程
   - 发起新问题
   - 在 Telegram 点击按钮
   - 验证答案传递

**优点**:
- 符合现有架构设计
- 无需修改代码
- 支持远程控制和会话管理
- 可以通过 `tmux attach -t claude` 查看会话

**缺点**:
- 需要重启当前 Claude Code 会话
- 当前对话上下文会丢失
- 需要手动操作

**适用场景**: 长期使用，需要稳定的远程控制

### 方案B：修改 webhook 代码适应当前环境

**步骤**:
1. 修改 `webhook_server.py` 的 `handle_callback_query()` 函数
2. 检测 Claude Code 的实际运行环境
3. 如果不在 tmux 中，使用替代方式发送答案

**可能的实现方式**:

**方式1：写入临时文件**
```python
# 写入答案到临时文件
answer_file = '/tmp/claude_answer.txt'
with open(answer_file, 'w') as f:
    f.write(answer_text)

# Claude Code 需要轮询读取
# 或通过文件监听机制
```

**方式2：通过进程信号**
```python
# 找到 Claude Code 进程
import psutil
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    if 'claude' in proc.info['name'].lower():
        # 发送信号或通过其他 IPC 机制
        pass
```

**方式3：HTTP 回调**
```python
# 如果 Claude Code 提供 HTTP 接口
requests.post('http://localhost:xxxx/answer', json={'answer': answer_text})
```

**优点**:
- 无需重启 Claude Code
- 更灵活的部署方式
- 支持多种运行环境

**缺点**:
- 需要修改代码，增加复杂度
- 可能影响其他功能
- 需要 Claude Code 配合（轮询或监听）
- 实现难度较高

**适用场景**: 需要支持多种部署方式，或无法使用 tmux

### 方案C：更新 config.json 配置

**步骤**:
1. 找到当前 Claude Code 实际使用的 session（如果有）
2. 更新 `config.json` 中的 `tmux_session` 配置
3. 重启 webhook 服务器

**示例**:
```json
{
  "claude": {
    "tmux_session": "p0-smart-filter",  // 或其他实际存在的 session
    ...
  }
}
```

**优点**:
- 最小改动
- 快速修复

**缺点**:
- 如果 Claude Code 不在 tmux 中，仍然无法工作
- 治标不治本
- 可能发送到错误的 session

**适用场景**: 临时测试，或确认 Claude Code 在某个 tmux session 中

## 测试验证

### 测试流程
1. 发起 AskUserQuestion
2. 检查 Telegram 是否显示问题和按钮
3. 在 Telegram 点击按钮
4. 检查 webhook 日志是否收到 callback_query
5. 检查 tmux send-keys 是否成功执行
6. 检查 Claude Code 是否收到答案
7. 验证 AskUserQuestion 返回正确结果

### 成功标准
- ✅ PreToolUse hook 触发（已验证）
- ✅ Telegram 显示问题和按钮（已验证）
- ✅ Webhook 接收 callback_query（已验证）
- ❌ Tmux send-keys 成功执行（失败 - session 不存在）
- ❌ Claude Code 收到答案（失败）
- ❌ AskUserQuestion 返回正确结果（失败）

### 测试日志
```
# PreToolUse hook 触发
2025-12-27 14:18:31,103 [INFO] Received Claude hook: ask_question, is_question=True, questions_count=1
2025-12-27 14:18:32,212 [INFO] Telegram message sent: 622
2025-12-27 14:18:32,214 [INFO] ✓ Question prompt sent with 2 options

# Callback query 接收
2025-12-27 14:18:56,923 [INFO] Received callback: ans_1766873911205_0
2025-12-27 14:18:56,924 [INFO] Sending task to Claude Code: 测试成功...

# Tmux 发送失败
2025-12-27 14:18:56,938 [ERROR] Failed to send task: Command '['tmux', 'send-keys', '-t', 'claude', '测试成功', 'C-m']' returned non-zero exit status 1.
2025-12-27 14:18:57,727 [INFO] Callback answered: ❌ 发送失败
```

## 相关文件

### 核心文件
- `webhook_server.py:693-759` - handle_callback_query() 函数
- `webhook_server.py:741-754` - 修复后的答案发送逻辑
- `webhook_server.py:482-510` - send_task_to_claude() 函数
- `webhook_server.py:85-90` - get_current_tmux_session() 函数
- `config.json:15-16` - tmux_session 配置

### 配置文件
- `.claude/settings.json` - PreToolUse hook 配置
- `config.json` - 完整配置（bot token, webhook, tmux session）

### 相关文档
- `docs/prds/bug-notification-hook-not-capturing-askuserquestion.md` - PreToolUse hook 修复
- `CLAUDE.md` - 项目架构和数据流说明

## 下一步行动

### 立即行动
1. **决定采用哪个解决方案**
   - 推荐：方案A（在 tmux 中运行 Claude Code）
   - 原因：符合架构设计，长期稳定

2. **如果选择方案A**:
   - [ ] 创建 tmux session "claude"
   - [ ] 在 session 中启动 Claude Code
   - [ ] 重新测试完整流程
   - [ ] 验证所有功能正常

3. **如果选择方案B**:
   - [ ] 设计答案传递机制
   - [ ] 修改 webhook_server.py
   - [ ] 实现 Claude Code 端的接收逻辑
   - [ ] 测试验证

4. **如果选择方案C**:
   - [ ] 确认 Claude Code 运行环境
   - [ ] 更新 config.json
   - [ ] 重启 webhook 服务器
   - [ ] 测试验证

### 后续优化
- [ ] 考虑使用固定域名替代 localtunnel（URL 会变化）
- [ ] 或配置 ngrok authtoken 使用 ngrok
- [ ] 添加更好的错误处理和日志记录
- [ ] 实现自动检测 Claude Code 运行环境
- [ ] 更新 CLAUDE.md 文档记录最终方案

## 技术债务

### 短期
- Localtunnel URL 会在重启后变化，需要重新设置 webhook
- 当前没有自动恢复机制

### 中期
- Webhook 服务器应该支持自动检测 Claude Code 运行环境
- 需要更健壮的错误处理（tmux session 不存在时的降级方案）

### 长期
- 考虑使用更稳定的公网暴露方案（固定域名、ngrok 付费版、Cloudflare Tunnel）
- 实现完整的进程间通信机制，不依赖 tmux
- 支持多种部署方式（tmux、systemd、Docker）

## 参考资料

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Localtunnel GitHub](https://github.com/localtunnel/localtunnel)
- [ngrok Documentation](https://ngrok.com/docs)
- [Tmux Wiki](https://github.com/tmux/tmux/wiki)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 时间线

- **2025-12-27 10:16** - 首次测试 PreToolUse hook 成功
- **2025-12-27 10:18-10:20** - 后续测试失败（hook 未完全生效）
- **2025-12-27 11:20** - 修复 callback_query 处理逻辑（单次 Enter）
- **2025-12-27 11:26** - PreToolUse hook 再次成功触发
- **2025-12-27 14:12** - 发现旧 webhook 配置错误（530 错误）
- **2025-12-27 14:16** - 安装 ngrok（需要 authtoken）
- **2025-12-27 14:16** - 改用 localtunnel
- **2025-12-27 14:17** - 设置新 webhook 成功
- **2025-12-27 14:18** - 测试发现 tmux session 不存在问题

## 状态

**当前状态**: ❌ 阻塞 - Tmux session 配置错误

**阻塞原因**: Claude Code 不在 tmux 中运行，无法通过 tmux send-keys 传递答案

**下一步**: 决定解决方案并实施

**预计解决时间**:
- 方案A: 10-15 分钟（创建 session + 重启 + 测试）
- 方案B: 1-2 小时（设计 + 实现 + 测试）
- 方案C: 5 分钟（更新配置 + 测试，但可能无效）
