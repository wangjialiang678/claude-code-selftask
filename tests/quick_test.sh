#!/bin/bash
# 快速测试脚本 - 添加单个测试任务并验证

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==================================================="
echo "Claude Code 自动任务系统 - 快速测试"
echo "==================================================="

# 添加最简单的测试任务
echo ""
echo "添加测试任务: test-create-file"
cat > data/dev-tasks.json <<EOF
{
  "tasks": [
    {
      "id": "test-create-file",
      "description": "创建文件 test-output.txt，内容为 'Test successful from $(date +%Y-%m-%d)'",
      "status": "pending",
      "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    }
  ]
}
EOF

echo "✓ 任务已添加到队列"
echo ""
echo "任务内容:"
cat data/dev-tasks.json | jq '.tasks[0]'
echo ""
echo "---------------------------------------------------"
echo "接下来："
echo "1. 启动 Worker（手动或自动）"
echo "2. Worker 会领取任务并执行"
echo "3. 执行此脚本的验证部分"
echo "---------------------------------------------------"
echo ""
read -p "Worker 完成后按回车验证..."

# 验证
echo ""
echo "验证结果..."

if [ -f "test-output.txt" ]; then
    echo "✓ 文件已创建: test-output.txt"
    echo "  内容:"
    cat test-output.txt | sed 's/^/    /'

    if grep -q "Test successful" test-output.txt; then
        echo ""
        echo "✓✓✓ 测试通过！Worker 正常工作 ✓✓✓"
        exit 0
    else
        echo ""
        echo "✗ 文件内容不正确"
        exit 1
    fi
else
    echo "✗ 文件不存在: test-output.txt"
    echo ""
    echo "可能的原因:"
    echo "  1. Worker 未启动"
    echo "  2. Worker 执行失败"
    echo "  3. 任务未被领取"
    exit 1
fi
