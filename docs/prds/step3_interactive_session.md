# 📋 Stage 3: Interactive Claude Code Session Management PRD

## 🎯 Stage 3 目标

实现从 Telegram 直接启动和管理 Claude Code 交互式会话，让用户能够：
- 从 Telegram 发送任务描述
- 自动启动 Claude Code 会话
- 实时接收执行进度和结果
- 简化整个工作流程

---

## 📊 当前状态 vs 目标状态

### 当前状态（Stage 2）

**用户工作流程：**
1. 在本地终端启动 Claude Code CLI
2. 手动输入任务描述
3. Claude Code 执行任务
4. Hooks 自动发送通知到 Telegram
5. 在 Telegram 查看结果

**限制：**
- 必须手动启动 Claude Code
- 无法从 Telegram 直接发起任务
- 需要访问本地终端

### 目标状态（Stage 3）

**理想工作流程：**
1. 在 Telegram 发送: `/ask 帮我分析这个项目的架构`
2. 系统自动启动 Claude Code 会话
3. 任务自动执行
4. 实时接收进度通知
5. 完成后收到完整结果

**优势：**
- 完全远程操作
- 无需访问本地终端
- 一键启动任务
- 更便捷的用户体验

---

## 🏗️ 技术方案

### 3.1 会话管理策略

#### 方案 A: 持久化 Claude Code 会话（推荐）

**原理：**
- 在 tmux 会话中保持一个活跃的 Claude Code CLI 实例
- 通过 stdin 注入用户的问题/任务
- 利用现有的 hooks 系统接收结果

**优点：**
- 无需每次启动 Claude Code（启动时间 ~2-3 秒）
- 保持对话上下文
- 更快的响应速度

**实现：**
```bash
# 启动持久化会话
tmux new-session -d -s claude "claude"

# 发送任务
tmux send-keys -t claude "帮我分析这个项目的架构" C-m
```

#### 方案 B: 按需启动会话

**原理：**
- 每次收到 `/ask` 命令时启动新的 Claude Code 实例
- 执行完成后自动退出

**优点：**
- 更清晰的会话隔离
- 无状态，易于调试

**缺点：**
- 每次启动耗时较长
- 无法保持对话上下文

**选择：方案 A（持久化会话）**

### 3.2 新增 Telegram 命令

#### `/ask <question>` - 发起任务

**功能：**
- 接收用户的任务描述
- 检查 Claude Code 会话状态
- 如果没有活跃会话，自动启动
- 将任务发送给 Claude Code
- 返回确认消息

**示例：**
```
用户: /ask 帮我重构 webhook_server.py 的错误处理逻辑

Bot: ✅ 任务已发送给 Claude Code
     正在执行中，请稍候...

     你将收到实时进度通知
```

#### `/session` - 查看会话状态

**功能：**
- 检查 tmux 会话是否存在
- 检查 Claude Code 是否运行
- 显示当前任务状态

**示例：**
```
用户: /session

Bot: 📊 会话状态

     Tmux Session: ✅ 运行中
     Claude Code: ✅ 活跃
     当前任务: 正在分析项目架构
     运行时间: 45 秒
```

#### `/start_claude` - 手动启动会话

**功能：**
- 手动启动 Claude Code 会话
- 用于会话崩溃后的恢复

**示例：**
```
用户: /start_claude

Bot: 🚀 正在启动 Claude Code 会话...
     ✅ 会话已启动

     现在可以使用 /ask 发送任务
```

#### `/stop_claude` - 停止会话

**功能：**
- 优雅地停止 Claude Code 会话
- 清理资源

---

## 🔧 实施步骤

### 3.1 更新 webhook_server.py

需要添加的功能：
1. 会话状态检测
2. 自动启动 Claude Code
3. 任务队列管理（可选）
4. 新命令处理器

### 3.2 会话管理函数

```python
def check_claude_session():
    """检查 Claude Code 会话是否运行"""
    try:
        # 检查 tmux 会话
        result = subprocess.run(
            ['tmux', 'has-session', '-t', TMUX_SESSION],
            capture_output=True
        )
        if result.returncode != 0:
            return False

        # 检查是否有 Claude Code 进程
        output = subprocess.check_output(
            ['tmux', 'capture-pane', '-t', TMUX_SESSION, '-p'],
            text=True
        )
        # 简单检测：看是否有 Claude Code 的提示符
        return 'claude>' in output.lower() or 'claude code' in output.lower()
    except:
        return False

def start_claude_session():
    """启动 Claude Code 会话"""
    try:
        # 创建 tmux 会话并启动 Claude Code
        subprocess.run(
            ['tmux', 'new-session', '-d', '-s', TMUX_SESSION, 'claude'],
            check=True
        )
        time.sleep(2)  # 等待启动
        return True
    except Exception as e:
        logger.error(f"Failed to start Claude session: {e}")
        return False

def send_task_to_claude(task):
    """发送任务给 Claude Code"""
    try:
        # 发送任务到 tmux 会话
        subprocess.run(
            ['tmux', 'send-keys', '-t', TMUX_SESSION, task, 'C-m'],
            check=True
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send task: {e}")
        return False
```

### 3.3 新命令处理器

```python
def handle_command(command):
    """处理 Telegram 命令"""
    cmd = command.lower().strip()

    if cmd.startswith('/ask '):
        # 提取任务描述
        task = command[5:].strip()

        if not task:
            send_telegram_message("❌ 请提供任务描述\n\n用法: /ask <你的问题>")
            return

        # 检查会话状态
        if not check_claude_session():
            send_telegram_message("🚀 Claude Code 会话未运行，正在启动...")
            if not start_claude_session():
                send_telegram_message("❌ 启动失败，请检查日志")
                return
            send_telegram_message("✅ 会话已启动")

        # 发送任务
        if send_task_to_claude(task):
            msg = f"""✅ 任务已发送给 Claude Code

📝 任务内容:
{task}

⏳ 正在执行中，请稍候...
你将收到实时进度通知"""
            send_telegram_message(msg)
        else:
            send_telegram_message("❌ 发送任务失败")

    elif cmd == '/session':
        # 检查会话状态
        session_exists = check_claude_session()

        if session_exists:
            # 获取当前输出
            try:
                output = subprocess.check_output(
                    ['tmux', 'capture-pane', '-t', TMUX_SESSION, '-p'],
                    text=True
                )
                last_lines = '\n'.join(output.split('\n')[-10:])

                msg = f"""📊 会话状态

✅ Tmux Session: 运行中
✅ Claude Code: 活跃

最近输出:
```
{last_lines}
```"""
                send_telegram_message(msg)
            except Exception as e:
                send_telegram_message(f"✅ 会话运行中\n❌ 无法获取输出: {e}")
        else:
            send_telegram_message("""❌ 会话未运行

使用 /start_claude 启动会话
或直接使用 /ask 发送任务（会自动启动）""")

    elif cmd == '/start_claude':
        if check_claude_session():
            send_telegram_message("✅ Claude Code 会话已经在运行")
        else:
            send_telegram_message("🚀 正在启动 Claude Code 会话...")
            if start_claude_session():
                send_telegram_message("""✅ 会话已启动

现在可以使用 /ask 发送任务""")
            else:
                send_telegram_message("❌ 启动失败，请检查日志")

    elif cmd == '/stop_claude':
        try:
            subprocess.run(['tmux', 'kill-session', '-t', TMUX_SESSION], check=True)
            send_telegram_message("✅ Claude Code 会话已停止")
        except:
            send_telegram_message("❌ 会话不存在或停止失败")

    # ... 保留原有的 /status, /help, /last_output 等命令
```

---

## 🧪 测试验证

### 测试 1: 自动启动会话

```
1. 确保没有运行的 Claude Code 会话
   tmux kill-session -t claude

2. 在 Telegram 发送:
   /ask 列出当前目录的文件

3. 验证:
   - 收到"正在启动会话"消息
   - 收到"任务已发送"消息
   - 收到 Claude Code 的执行结果通知
```

### 测试 2: 持久化会话

```
1. 发送第一个任务:
   /ask 读取 config.json 文件

2. 等待完成后，立即发送第二个任务:
   /ask 这个配置文件有哪些字段？

3. 验证:
   - 第二个任务立即执行（无需重新启动）
   - Claude Code 能够引用之前的上下文
```

### 测试 3: 会话状态查询

```
1. 发送:
   /session

2. 验证:
   - 显示会话运行状态
   - 显示最近的输出
```

### 测试 4: 错误恢复

```
1. 手动杀死 Claude Code 进程:
   tmux kill-session -t claude

2. 发送:
   /ask 测试任务

3. 验证:
   - 系统检测到会话不存在
   - 自动重新启动
   - 任务正常执行
```

---

## 📋 验收标准

### 功能测试

- ✅ `/ask` 命令能成功发送任务给 Claude Code
- ✅ 无会话时自动启动 Claude Code
- ✅ 任务执行结果通过 hooks 发送到 Telegram
- ✅ `/session` 正确显示会话状态
- ✅ `/start_claude` 能手动启动会话
- ✅ `/stop_claude` 能优雅停止会话
- ✅ 持久化会话保持对话上下文

### 性能测试

- 首次启动会话: < 5 秒
- 发送任务到执行: < 2 秒
- 会话保持稳定: 24 小时无崩溃

### 用户体验测试

- 命令响应清晰明确
- 错误消息有帮助性
- 进度通知及时

---

## 🎯 用户体验优化

### 智能提示

当用户发送 `/ask` 但任务描述不清晰时，给出建议：

```
用户: /ask 帮我

Bot: ❌ 任务描述太简短

💡 建议的任务格式:
- /ask 分析 webhook_server.py 的性能瓶颈
- /ask 重构错误处理逻辑
- /ask 添加日志记录功能
- /ask 解释 config.json 的配置项
```

### 进度指示

对于长时间运行的任务，定期发送进度更新：

```
✅ 任务已发送 (0s)
⏳ 正在执行中... (30s)
⏳ 仍在执行中... (60s)
✅ 任务完成 (90s)
```

### 快捷命令

添加常用任务的快捷方式：

```
/analyze <file> - 分析指定文件
/refactor <file> - 重构指定文件
/explain <concept> - 解释概念
/debug <error> - 调试错误
```

---

## 🔄 与现有系统的集成

### 保持向后兼容

- 所有 Stage 1 和 Stage 2 的功能继续工作
- `/status`, `/help`, `/last_output`, `/claude` 命令保持不变
- 现有的 hooks 系统无需修改

### 配置更新

在 `config.json` 中添加新配置：

```json
{
  "claude": {
    "tmux_session": "claude",
    "auto_start": true,
    "session_timeout": 3600,
    "max_task_length": 1000
  }
}
```

---

## 🚀 实施计划

### 阶段 1: 核心功能（必须）

1. 实现会话检测和启动逻辑
2. 添加 `/ask` 命令
3. 添加 `/session` 命令
4. 测试基本流程

### 阶段 2: 增强功能（推荐）

1. 添加 `/start_claude` 和 `/stop_claude`
2. 实现智能提示
3. 添加进度指示
4. 优化错误处理

### 阶段 3: 高级功能（可选）

1. 任务队列管理
2. 多会话支持
3. 任务历史记录
4. 快捷命令

---

## 📊 预期效果

### 使用前（Stage 2）

```
1. SSH 到服务器
2. 启动 tmux
3. 运行 claude
4. 输入任务
5. 等待结果
6. 在 Telegram 查看通知
```

总步骤: 6 步，需要终端访问

### 使用后（Stage 3）

```
1. 在 Telegram 发送: /ask <任务>
2. 接收结果通知
```

总步骤: 2 步，完全远程

**效率提升: 3x**

---

## 🎯 成功指标

- 用户从 Telegram 发起任务的成功率 > 95%
- 平均任务启动时间 < 5 秒
- 会话稳定性: 24 小时无需重启
- 用户满意度: 简化工作流程，提高效率

---

## 下一步

完成 Stage 3 后，系统将实现完整的远程 Claude Code 控制能力。

**可能的扩展方向：**
- 多用户支持
- 任务调度和队列
- 更丰富的交互方式（按钮、内联键盘）
- 集成更多 Claude Code 功能
