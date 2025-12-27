# P2 多项目支持 - 验收清单

## 配置结构

- [ ] config.json 包含 projects 对象
- [ ] 每个项目配置包含 name, path, tmux_session, notification_level
- [ ] config.json 包含 active_project 字段
- [ ] 配置文件格式验证通过

## 项目管理

- [ ] ProjectManager 类正确加载配置
- [ ] get_active_project() 返回当前活跃项目
- [ ] switch_project() 切换项目并保存配置
- [ ] get_project_status() 返回项目状态（tmux会话、通知级别）
- [ ] 切换不存在的项目返回错误

## 命令实现

- [ ] /projects 列出所有项目
- [ ] /projects 显示项目名称、ID、状态
- [ ] /projects 标记当前活跃项目（✅）
- [ ] /projects 显示 tmux 会话状态（🟢/🔴）
- [ ] /switch <project-id> 切换项目
- [ ] /switch 成功后返回确认消息
- [ ] /ask@<project-id> <任务> 向指定项目发送任务
- [ ] @语法正确解析项目ID和任务内容

## 独立历史记录

- [ ] 每个项目有独立的历史文件 logs/tool_history_<project-id>.json
- [ ] 历史记录自动保存到对应项目文件
- [ ] /history 默认查询当前活跃项目
- [ ] /history@<project-id> 查询指定项目历史
- [ ] 项目切换后历史查询自动切换到新项目

## 通知级别

- [ ] 每个项目的 notification_level 独立生效
- [ ] 切换项目后通知级别自动切换
- [ ] /level 命令修改当前项目的通知级别
- [ ] 通知级别变更保存到配置文件

## 功能测试

- [ ] 配置2个项目，/projects 显示2个项目
- [ ] /switch project-b 切换成功
- [ ] /ask@project-a 任务发送到 project-a 的 tmux 会话
- [ ] project-a 设置为 minimal，project-b 设置为 normal，通知行为正确
- [ ] 每个项目的历史记录独立存储

## 性能测试

- [ ] 项目切换延迟 < 2秒
- [ ] 支持至少5个项目同时配置
- [ ] 历史查询跨项目不影响性能

## 错误处理

- [ ] 切换不存在的项目返回错误
- [ ] @语法错误返回友好提示
- [ ] 项目配置缺失字段时使用默认值
- [ ] tmux 会话不存在时显示离线状态

## 向后兼容

- [ ] 旧的单项目配置自动迁移到新格式
- [ ] 没有 projects 配置时使用默认项目
- [ ] 现有功能在单项目模式下正常工作
