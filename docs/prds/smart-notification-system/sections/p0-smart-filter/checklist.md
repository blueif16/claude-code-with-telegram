# P0 智能过滤 - 验收清单

## 配置文件

- [x] config.json 添加 notification.level 字段（默认 "normal"）
- [x] config.json 添加 notification.always_notify_events 列表
- [x] config.json 添加 notification.silent_tools 列表

## Hook 脚本

- [x] notify-telegram-smart.sh 实现 should_notify() 函数
- [x] should_notify() 正确处理 minimal 模式
- [x] should_notify() 正确处理 normal 模式
- [x] should_notify() 正确处理 verbose 模式
- [x] 脚本在发送前调用 should_notify() 判断

## Webhook 服务器

- [x] webhook_server.py 添加 tool_history 全局变量
- [x] /claude-hook 端点记录所有事件到历史
- [x] 历史记录包含 timestamp、event、data 字段
- [x] 根据 notification_level 决定是否发送 Telegram 消息

## 功能测试

- [x] minimal 模式：只收到 stop 和 error 通知
- [x] normal 模式：收到 stop、error、permission、question 通知
- [x] normal 模式：不收到 Read、Grep、Glob、Edit、Write 通知
- [x] verbose 模式：收到所有通知
- [x] 所有模式下历史记录都完整

## 性能指标

- [x] normal 模式下通知数量减少约 80%
- [x] 历史记录不超过 1000 条（需要实现清理机制）
- [x] 过滤逻辑不影响 hook 执行速度（< 100ms）

## 日志验证

- [x] webhook.log 记录所有接收到的事件
- [x] webhook.log 记录过滤决策（发送/跳过）
- [x] hooks.log 记录 should_notify() 的判断结果
