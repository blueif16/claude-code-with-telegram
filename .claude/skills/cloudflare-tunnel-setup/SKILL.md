# Cloudflare Tunnel Setup for Webhook

## 目的
快速设置 Cloudflare Tunnel 并配置 Telegram webhook，实现本地服务的公网访问。

## 前置条件
- 已安装 cloudflared: `brew install cloudflared`
- 已登录 Cloudflare: `cloudflared tunnel login`
- 本地 webhook 服务器运行在 8000 端口
- 有 Telegram bot token 和 secret token

## 执行步骤

### 1. 检查现有 Tunnel

```bash
cloudflared tunnel list
```

如果已有 tunnel（如 claude-bot），记录其 ID 和名称。

### 2. 创建 DNS 路由（如果还没有）

```bash
cloudflared tunnel route dns <tunnel-name> <subdomain>.<domain>
```

示例：
```bash
cloudflared tunnel route dns claude-bot claude-bot.blueif.me
```

### 3. 生成 Credentials 文件

```bash
cloudflared tunnel token --cred-file ~/.cloudflared/<tunnel-id>.json <tunnel-name>
```

### 4. 创建配置文件

创建 `~/.cloudflared/config.yml`:

```yaml
tunnel: <tunnel-id>
credentials-file: /Users/<username>/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: <subdomain>.<domain>
    service: http://localhost:8000
  - service: http_status:404
```

### 5. 启动 Tunnel

```bash
cloudflared tunnel run <tunnel-name>
```

或后台运行：
```bash
nohup cloudflared tunnel run <tunnel-name> > /tmp/cloudflared.log 2>&1 &
```

### 6. 验证 Tunnel

```bash
curl https://<subdomain>.<domain>/health
```

应该返回 webhook 服务器的 health 响应。

### 7. 配置 Telegram Webhook

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://<subdomain>.<domain>/telegram-webhook" \
  -d "secret_token=<SECRET_TOKEN>"
```

### 8. 验证 Webhook

```bash
curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo" | python3 -m json.tool
```

检查：
- `url` 正确
- `pending_update_count` 为 0
- `ip_address` 存在

## 快速命令（完整流程）

假设：
- Tunnel 名称: claude-bot
- Tunnel ID: 6d5c7013-2b0e-45f7-877f-e177b84f51ec
- 域名: claude-bot.blueif.me
- Bot token: 从 config.json 获取
- Secret token: 从 config.json 获取

```bash
# 1. 创建 DNS 路由
cloudflared tunnel route dns claude-bot claude-bot.blueif.me

# 2. 生成 credentials
cloudflared tunnel token --cred-file ~/.cloudflared/6d5c7013-2b0e-45f7-877f-e177b84f51ec.json claude-bot

# 3. 创建配置（手动编辑 ~/.cloudflared/config.yml）

# 4. 启动 tunnel
cloudflared tunnel run claude-bot &

# 5. 验证
curl https://claude-bot.blueif.me/health

# 6. 设置 webhook
BOT_TOKEN=$(grep '"bot_token"' config.json | cut -d'"' -f4)
SECRET_TOKEN=$(grep '"secret_token"' config.json | cut -d'"' -f4)

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=https://claude-bot.blueif.me/telegram-webhook" \
  -d "secret_token=${SECRET_TOKEN}"

# 7. 验证 webhook
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool
```

## 常见问题

### Tunnel 返回 404
- 检查 config.yml 中的 service URL 是否正确
- 确认本地服务器在 8000 端口运行
- 重启 tunnel

### Webhook 不接收消息
- 检查 secret_token 是否匹配
- 查看 webhook 服务器日志: `tail -f logs/webhook.log`
- 检查 Cloudflare tunnel 日志

### Tunnel 连接断开
- 使用 systemd 或 launchd 管理 tunnel 进程
- 或使用 tmux/screen 保持运行

## 工具
- Bash
- Read
- Write
