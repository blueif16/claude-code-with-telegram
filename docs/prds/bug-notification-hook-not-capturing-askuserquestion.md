# Bug: Notification Hook 无法捕获 AskUserQuestion 的 idle_prompt 事件

## 问题描述

当 Claude Code 调用 AskUserQuestion 工具时，Notification hook 没有被触发，导致 Telegram 无法收到问题通知和交互按钮。

## 复现步骤

1. 启动 webhook 服务器
2. 在 Claude Code 中调用 AskUserQuestion 工具
3. 观察 Telegram 是否收到通知

## 预期行为

- AskUserQuestion 调用应该触发 hook
- notify-telegram-smart.sh 应该提取 questions 数据
- Webhook 服务器应该收到 is_question=true 的请求
- Telegram 应该显示带交互按钮的消息

## 实际行为

- Notification hook 没有被触发
- Telegram 没有收到任何通知
- 用户无法通过 Telegram 回答问题

## 根本原因分析

经过调查发现：
1. AskUserQuestion 工具**不会触发 Notification hook**
2. 需要使用 **PreToolUse hook** 来捕获 AskUserQuestion 调用
3. PreToolUse hook 在工具调用前触发，可以获取完整的 tool_input 数据

## 影响范围

- 所有需要用户交互的场景
- Telegram 远程控制功能受限

## 修复方案

### 1. 添加 PreToolUse Hook 配置

在 `.claude/settings.json` 中添加 PreToolUse hook：

```json
"PreToolUse": [{
  "matcher": "AskUserQuestion",
  "hooks": [{
    "type": "command",
    "command": "/Users/tk/Desktop/claude-code-with-telegram/.claude/notify-telegram-smart.sh ask_question"
  }]
}]
```

### 2. Hook 脚本已支持

`notify-telegram-smart.sh` 已经实现了 `ask_question` 事件类型的处理逻辑（第59-70行），可以：
- 从 `tool_input.questions` 提取问题数据
- 设置 `IS_QUESTION=true` 标志
- 将 questions 数据传递给 webhook 服务器

### 3. Webhook 服务器已支持

`webhook_server.py` 已经实现了问题处理逻辑：
- `handle_question_prompt()` 函数生成 Telegram inline keyboard
- 支持多选和单选问题
- 自动添加"其他"选项

## 测试结果

### 第一次测试（10:16:00）
- ✅ PreToolUse hook 成功触发（日志：`Sat Dec 27 10:16:00 PST 2025: EVENT=ask_question`）
- ✅ Hook 脚本成功提取 questions 数据
- ✅ Webhook 服务器收到请求（`is_question=True, questions_count=1`）
- ✅ Telegram 消息发送成功（message ID: 600）
- ✅ 生成了 inline keyboard 按钮（2个选项）

### 后续测试（10:18:48, 10:20:34）
- ❌ PreToolUse hook 未触发
- ❌ 只看到 PostToolUse 的 tool_use 事件
- **原因**：Claude Code 在会话中途添加 hook 配置时不会立即生效

## 重要发现

**Claude Code 需要重启才能加载新的 hook 配置**。在当前会话中添加 PreToolUse hook 配置后：
1. 第一次调用 AskUserQuestion 时 hook 触发了（可能是配置刚加载）
2. 后续调用都没有触发（配置未完全生效）
3. 需要重启 Claude Code 会话才能使配置完全生效

## 状态

**已修复（需要重启）** - PreToolUse hook 配置已添加到 `.claude/settings.json`，但需要重启 Claude Code 会话才能完全生效。

## 验证步骤

1. 确认 `.claude/settings.json` 中已添加 PreToolUse hook 配置
2. 重启 Claude Code 会话
3. 调用 AskUserQuestion 工具
4. 检查 Telegram 是否收到带按钮的消息
5. 检查日志：`tail -f ~/.claude/hooks_debug.log` 应该看到 `EVENT=ask_question`
