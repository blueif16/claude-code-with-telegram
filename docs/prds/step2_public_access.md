# 📋 Stage 2: Public Access via Cloudflare Tunnel PRD

## 🎯 Stage 2 目标

实现通过 Cloudflare Tunnel 的公网访问，使 Telegram Bot 能够从任何地方（手机、外网）与本地 Claude Code 通信。

---

## 📊 背景

Stage 1 完成了本地验证，所有组件在本地网络正常工作：
- ✅ Webhook 服务器运行正常
- ✅ Claude Code hooks 能发送通知到 Telegram
- ✅ Telegram 命令能控制本地 tmux 会话

**Stage 2 的挑战：**
- Telegram 的 webhook 需要公网 HTTPS 地址
- 本地开发机器通常没有公网 IP
- 需要安全的隧道方案，避免暴露本地网络

**解决方案：Cloudflare Tunnel**
- 免费、安全、无需开放端口
- 自动 HTTPS 证书
- 稳定的连接管理

---

## 🏗️ 架构变化

### Stage 1 架构（本地）
```
Claude Code → Hook Script → Webhook (localhost:8000) → Telegram API
                                ↑
                          Telegram (手动 curl 测试)
```

### Stage 2 架构（公网）
```
Claude Code → Hook Script → Webhook (localhost:8000) ← Cloudflare Tunnel ← Telegram API
                                                              ↑
                                                        公网 HTTPS 地址
                                                     (webhook.blueif.me)
```

---

## 🔧 实施步骤

### 2.1 安装 Cloudflare Tunnel

**Linux (WSL2):**
```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
cloudflared --version
```

**macOS:**
```bash
brew install cloudflare/cloudflare/cloudflared
```

### 2.2 配置 Cloudflare Tunnel

```bash
# 1. 登录 Cloudflare（会打开浏览器）
cloudflared tunnel login

# 2. 创建 tunnel
cloudflared tunnel create claude-bot
# 输出: Created tunnel claude-bot with id 6d5c7013-2b0e-45f7-877f-e177b84f51ec

# 3. 配置 DNS 路由
cloudflared tunnel route dns claude-bot webhook.blueif.me
# 输出: Created CNAME record for webhook.blueif.me
```

### 2.3 创建 Tunnel 配置文件

创建 `~/.cloudflared/config.yml`:
```yaml
tunnel: 6d5c7013-2b0e-45f7-877f-e177b84f51ec
credentials-file: /home/ran/.cloudflared/6d5c7013-2b0e-45f7-877f-e177b84f51ec.json

ingress:
  - hostname: webhook.blueif.me
    service: http://localhost:8000
  - service: http_status:404
```

### 2.4 启动 Tunnel

```bash
# 前台运行（测试）
cloudflared tunnel run claude-bot

# 成功输出：
# INF Registered tunnel connection connIndex=0
# INF Registered tunnel connection connIndex=1
# INF Registered tunnel connection connIndex=2
# INF Registered tunnel connection connIndex=3
```

### 2.5 更新安全配置

生成新的 secret token:
```bash
openssl rand -hex 32
```

更新 `config.json`:
```json
{
  "telegram": {
    "secret_token": "<新生成的64字符随机字符串>"
  }
}
```

### 2.6 配置 Telegram Webhook

```bash
# 设置 webhook
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://webhook.blueif.me/telegram-webhook" \
  -d "secret_token=<你的secret_token>"

# 验证配置
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

预期输出:
```json
{
  "ok": true,
  "result": {
    "url": "https://webhook.blueif.me/telegram-webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "max_connections": 40
  }
}
```

---

## 🧪 测试验证

### 测试 1: 公网健康检查
```bash
curl https://webhook.blueif.me/health
```

预期输出:
```json
{
  "status": "ok",
  "timestamp": "2025-12-15T...",
  "last_outputs": {...}
}
```

### 测试 2: Telegram 命令测试

在 Telegram App 中依次发送:

1. `/help` - 应该收到帮助信息
2. `/status` - 应该收到 tmux 会话输出
3. `/last_output` - 应该收到最后一次完整响应
4. `/claude echo "hello from telegram"` - 命令应该在 tmux 中执行

### 测试 3: Claude Code 通知测试

```bash
# 模拟 Claude Code 完成任务
echo '{"response":"Public test from Claude Code","duration_ms":1234,"timestamp":"2025-12-15T10:00:00Z"}' | \
  ~/.claude/notify-telegram-smart.sh stop
```

验证: 手机 Telegram 应该收到格式化的通知消息

### 测试 4: 端到端流程

1. 在 Claude Code 中执行一个实际任务
2. 任务完成时，Stop hook 自动触发
3. 手机 Telegram 收到通知（包含实际输出）
4. 发送 `/last_output` 查看完整响应

---

## 📋 验收标准

### 必须通过的测试

- ✅ Cloudflare Tunnel 安装和配置完成
- ✅ DNS 路由配置成功（webhook.blueif.me 可访问）
- ✅ 公网访问测试通过（curl https://webhook.blueif.me/health）
- ✅ Telegram webhook 配置成功
- ✅ 手机 Telegram 能接收 Claude Code 通知
- ✅ 手机 Telegram 能发送命令并收到响应
- ✅ 所有 Telegram 命令正常工作（/status, /help, /last_output, /claude）
- ✅ 24 小时稳定运行测试

### 性能指标

- 通知延迟: < 3 秒（从 hook 触发到 Telegram 接收）
- 命令响应: < 5 秒（从 Telegram 发送到收到响应）
- Tunnel 连接: 4 个连接保持活跃
- 无内存泄漏或连接泄漏

---

## 🔒 安全配置

### 已实施的安全措施

1. **Secret Token 验证**
   - 64 字符随机字符串
   - 每个 webhook 请求必须携带正确的 token
   - 错误的 token 返回 403

2. **Chat ID 白名单**
   - 只有配置的 chat_id 能发送命令
   - 未授权的 chat_id 被拒绝

3. **命令黑名单**
   - 危险命令（rm, dd, format, shutdown）被禁止
   - 可在 config.json 中配置

4. **HTTPS 加密**
   - Cloudflare Tunnel 自动提供 HTTPS
   - 所有通信加密传输

---

## 🚀 生产部署（可选）

### 后台运行

```bash
# Webhook 服务器
nohup python3 webhook_server.py > logs/webhook.log 2>&1 &

# Cloudflare Tunnel
nohup cloudflared tunnel run claude-bot > logs/tunnel.log 2>&1 &
```

### 查看运行状态

```bash
# 查看进程
ps aux | grep webhook_server
ps aux | grep cloudflared

# 查看日志
tail -f logs/webhook.log
tail -f logs/tunnel.log
tail -f ~/.claude/hooks.log
```

### 停止服务

```bash
# 停止 webhook
pkill -f webhook_server.py

# 停止 tunnel
pkill -f cloudflared
```

---

## 🐛 故障排查

### 问题 1: Telegram 收不到消息

**检查步骤:**
```bash
# 1. 验证 webhook 配置
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# 2. 检查 tunnel 状态
ps aux | grep cloudflared

# 3. 测试公网访问
curl https://webhook.blueif.me/health

# 4. 查看日志
tail -f logs/webhook.log
```

### 问题 2: Tunnel 连接不稳定

**解决方案:**
```bash
# 重启 tunnel
pkill -f cloudflared
cloudflared tunnel run claude-bot

# 检查 DNS 配置
nslookup webhook.blueif.me
```

### 问题 3: Webhook 返回 403

**原因:** Secret token 不匹配

**解决:**
1. 检查 config.json 中的 secret_token
2. 重新设置 Telegram webhook
3. 确保两边的 token 一致

---

## 📊 Stage 2 完成总结

### 已完成的配置

1. ✅ Cloudflare Tunnel 安装和配置
2. ✅ DNS 路由设置（webhook.blueif.me）
3. ✅ 安全配置（secret token, chat ID 验证）
4. ✅ Telegram webhook 配置
5. ✅ 双向通信测试通过

### 当前运行的服务

- Webhook 服务器: http://127.0.0.1:8000
- Cloudflare Tunnel: https://webhook.blueif.me
- Telegram Bot: 已配置 webhook

### 可用的功能

- ✅ Claude Code → Telegram 通知（实时）
- ✅ Telegram → Claude Code 命令执行
- ✅ 远程查看 tmux 状态
- ✅ 远程执行命令

---

## 🎯 下一步：Stage 3

Stage 2 完成后，系统已经可以：
- 从任何地方接收 Claude Code 通知
- 从手机远程控制 Claude Code

**Stage 3 目标：**
- 从 Telegram 直接启动 Claude Code 交互式会话
- 发送任务描述，自动执行并返回结果
- 更智能的会话管理和状态跟踪

详见: `step3_interactive_session.md`
