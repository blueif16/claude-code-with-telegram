#!/bin/bash
# InfiStack 子协调器启动脚本

SECTION_ID="$1"
WORKTREE_PATH="$2"

echo "=== InfiStack 子协调器 ==="
echo "Section: $SECTION_ID"
echo "Worktree: $WORKTREE_PATH"
echo ""

# 读取任务文件
if [ -f ".infistack/task.md" ]; then
    echo "任务说明:"
    cat .infistack/task.md
    echo ""
    echo "=========================="
    echo ""
    echo "请开始执行任务。完成后输出: COMPLETE: $SECTION_ID"
else
    echo "错误: 找不到任务文件 .infistack/task.md"
    exit 1
fi
