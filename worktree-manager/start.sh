#!/bin/bash
# 启动 Claude Code Worker Manager

cd "$(dirname "$0")"

echo "========================================="
echo "🚀 Claude Code Worker Manager"
echo "========================================="
echo ""

# 激活虚拟环境并启动
./venv/bin/python main.py
