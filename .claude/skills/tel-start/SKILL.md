---
name: tel-start
description: 启动 Telegram Webhook 服务器
allowed-tools: Bash, Read
---

# 启动 Telegram Webhook 服务器

## 目的
快速启动 Claude Code + Telegram 集成系统的本地 webhook 服务器，自动处理依赖检查和配置验证。

## 执行逻辑

### 1. 前置检查

调用模板脚本进行依赖检查：
```bash
./.claude/templates/check-dependencies.sh
```

脚本返回 JSON 格式结果，包含：
- `success`: 是否通过检查
- `installed`: 已安装的依赖列表
- `missing`: 缺失的依赖列表
- `exit_code`: 退出码

如果检查失败，显示缺失的依赖并提示运行 `./setup.sh`。

### 2. 验证配置

调用模板脚本进行配置验证：
```bash
./.claude/templates/validate-config.sh
```

脚本返回 JSON 格式结果，包含：
- `success`: 是否验证通过
- `valid_fields`: 有效的配置字段
- `missing_fields`: 缺失的配置字段
- `warnings`: 警告信息（如默认值未修改）

如果验证失败，显示缺失字段并提示编辑 config.json。

### 3. 启动服务器

调用模板脚本启动服务器：
```bash
./.claude/templates/start-server.sh
```

脚本自动处理：
- 创建日志目录
- 检查端口占用
- 后台启动服务器
- 健康检查验证

脚本返回 JSON 格式结果，包含：
- `success`: 是否启动成功
- `pid`: 服务器进程 ID
- `host`: 服务器地址
- `port`: 服务器端口
- `health_url`: 健康检查 URL
- `log_file`: 日志文件路径

### 4. 显示结果

根据脚本返回的 JSON 结果，格式化显示启动信息。

## 工具需求
- Bash（调用模板脚本）
- Read（读取脚本输出）

## 成功输出

```
✅ 依赖检查通过
✅ 配置验证通过
✅ 环境准备完成
🚀 启动 webhook 服务器...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 Webhook 服务器已启动
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 服务地址: http://127.0.0.1:8000
📊 健康检查: http://127.0.0.1:8000/health
📝 日志文件: logs/webhook.log

可用端点:
  • /claude-hook - 接收 Claude Code 通知
  • /telegram-webhook - 接收 Telegram 命令
  • /health - 健康检查

按 Ctrl+C 停止服务器
```

## 错误处理

### 缺少依赖
```
❌ 缺少依赖: tmux, jq
请运行: ./setup.sh
```

### 配置无效
```
❌ config.json 配置无效
请检查以下字段:
  • telegram.bot_token
  • telegram.chat_id
```

### 端口被占用
```
⚠️  端口 8000 已被占用
PID: 12345 (python3 webhook_server.py)

是否终止现有进程？[y/N]
```

## 使用场景

1. **首次启动**
   - 用户运行 `/tel-start`
   - 自动检查并提示缺失的配置

2. **日常使用**
   - 快速启动服务器
   - 无需记忆命令和参数

3. **调试模式**
   - 设置 `TEST_MODE=1` 环境变量
   - 模拟 Telegram API 调用

## 相关命令

- `./setup.sh` - 完整设置向导
- `./check_dependencies.sh` - 仅检查依赖
- `./tests/test_local_only.sh` - 测试本地功能
