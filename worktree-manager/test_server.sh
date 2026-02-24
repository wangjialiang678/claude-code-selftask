#!/bin/bash
# 测试 Worker Manager Web 界面

echo "========================================="
echo "测试 Claude Code Worker Manager"
echo "========================================="
echo ""

# 1. 验证静态文件
echo "1. 检查静态文件..."
if [ -f "static/index.html" ] && [ -f "static/style.css" ] && [ -f "static/app.js" ]; then
    echo "   ✓ 所有静态文件存在"
else
    echo "   ✗ 静态文件缺失"
    exit 1
fi

# 2. 验证 Python 依赖
echo "2. 检查 Python 依赖..."
./venv/bin/python -c "import fastapi, uvicorn, websockets; print('   ✓ 依赖已安装')" || {
    echo "   ✗ 依赖缺失"
    exit 1
}

# 3. 验证应用配置
echo "3. 检查应用配置..."
./venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from main import app
print(f'   ✓ FastAPI 应用加载成功')
print(f'   ✓ 路由数量: {len(app.routes)}')
" || {
    echo "   ✗ 应用配置错误"
    exit 1
}

# 4. 验证数据目录
echo "4. 检查数据目录..."
if [ -f "../data/dev-tasks.json" ]; then
    echo "   ✓ 任务文件存在"
else
    echo "   ! 任务文件不存在，将自动创建"
fi

echo ""
echo "========================================="
echo "所有检查通过！"
echo "========================================="
echo ""
echo "启动服务器："
echo "  cd /Users/michael/projects/claude-code-selftask/worktree-manager"
echo "  ./venv/bin/python main.py"
echo ""
echo "访问地址："
echo "  本地: http://localhost:8000"
echo "  局域网: http://$(ipconfig getifaddr en0 2>/dev/null || echo 'YOUR_IP'):8000"
echo ""
echo "API 文档："
echo "  http://localhost:8000/docs"
echo ""
