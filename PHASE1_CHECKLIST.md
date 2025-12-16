# Phase 1 本地验证阶段 - 实施清单

## 📋 前置准备检查

- [ ] Python 3.8+ 已安装 (`python3 --version`)
- [ ] tmux 已安装 (`tmux -V`)
- [ ] jq 已安装 (`jq --version`)
- [ ] curl 已安装 (`curl --version`)
- [ ] 已从 @BotFather 获得 Bot Token
- [ ] 已获得你的 Chat ID

### 获取 Chat ID 步骤
1. 打开 Telegram，搜索你的 bot
2. 点击 START 或发送任意消息
3. 访问: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. 在 JSON 中找到 `message.chat.id`

---

## 🔧 文件创建清单

- [ ] `config.json` - 配置文件（需填写 bot_token 和 chat_id）
- [ ] `requirements.txt` - Python 依赖
- [ ] `webhook_server.py` - Webhook 服务器
- [ ] `~/.claude/notify-telegram-smart.sh` - 智能通知脚本
- [ ] `~/.claude/settings.json` - Claude Code hooks 配置
- [ ] `tests/test_hook.sh` - Hook 测试脚本
- [ ] `tests/test_webhook.sh` - Webhook 测试脚本
- [ ] `tests/test_telegram.sh` - Telegram 命令测试脚本

---

## 📝 配置步骤

### 1. 配置文件设置
- [ ] 编辑 `config.json`，填写你的 `bot_token`
- [ ] 编辑 `config.json`，填写你的 `chat_id`
- [ ] 修改 `secret_token` 为随机字符串

### 2. 安装依赖
- [ ] 运行: `pip3 install -r requirements.txt`

### 3. 设置权限
- [ ] 运行: `chmod +x ~/.claude/notify-telegram-smart.sh`
- [ ] 运行: `chmod +x tests/*.sh`

---

## 🧪 测试清单

### 测试 1: Webhook 服务器启动
- [ ] 启动服务器: `python3 webhook_server.py`
- [ ] 验证输出包含: "Running on http://127.0.0.1:8000"
- [ ] 健康检查: `curl http://localhost:8000/health`

### 测试 2: Claude Hook → Telegram 通知
- [ ] 运行: `./tests/test_hook.sh`
- [ ] 验证 Telegram 收到格式化消息
- [ ] 验证消息包含响应文本、时长、时间戳

### 测试 3: 创建 tmux Session
- [ ] 运行: `tmux new-session -d -s claude`
- [ ] 验证: `tmux list-sessions | grep claude`

### 测试 4: Telegram → Webhook 接收
- [ ] 运行: `./tests/test_webhook.sh`
- [ ] 验证 curl 返回 200
- [ ] 验证 Telegram 收到 tmux 输出

### 测试 5: 端到端流程
- [ ] 在 Telegram 发送: `/status`
- [ ] 验证收到当前 tmux 输出
- [ ] 在 Telegram 发送: `/help`
- [ ] 验证收到帮助信息
- [ ] 在 Telegram 发送: `/claude echo "test"`
- [ ] 验证命令在 tmux 中执行

---

## ✅ Phase 1 完成标准

### 必须通过的测试
- [ ] Webhook 服务器稳定运行
- [ ] 本地 curl 触发通知，Telegram 正确接收（延迟 < 2s）
- [ ] 通知包含实际的 Claude 输出（不只是通用消息）
- [ ] Telegram 发送命令，webhook 正确解析
- [ ] tmux 命令执行成功
- [ ] `/status` 返回实际 tmux 输出
- [ ] `/last_output` 返回完整响应
- [ ] 所有日志正常记录

### 失败条件（不要进入 Phase 2）
- [ ] Telegram 消息延迟 > 5 秒
- [ ] 收到的是通用消息而不是实际输出
- [ ] tmux 命令执行失败
- [ ] 出现未处理的异常

---

## 🚨 故障排查

### Telegram 收不到消息
```bash
# 测试 Bot Token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# 手动发送测试
curl -X POST https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage \
  -d "chat_id=<YOUR_CHAT_ID>" \
  -d "text=Test"
```

### Hook 没有触发
```bash
# 检查脚本权限
ls -la ~/.claude/notify-telegram-smart.sh

# 测试 Hook 脚本
echo '{"response":"test"}' | ~/.claude/notify-telegram-smart.sh stop

# 检查日志
tail -f ~/.claude/hooks.log
```

### Webhook 收不到请求
```bash
# 检查端口
lsof -i :8000

# 检查进程
ps aux | grep webhook_server.py

# 查看日志
tail -f logs/webhook.log
```

---

## 📚 快速命令参考

```bash
# 启动服务
python3 webhook_server.py

# 查看日志
tail -f logs/webhook.log
tail -f ~/.claude/hooks.log

# 测试 Hook
echo '{"response":"test","duration_ms":123}' | \
  ~/.claude/notify-telegram-smart.sh stop

# 测试 Webhook
curl http://localhost:8000/health
```
