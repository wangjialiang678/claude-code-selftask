#!/bin/bash
# 启动 Claude Code Worker Manager + Go ASR Server

set -e

cd "$(dirname "$0")"

echo "========================================="
echo "🚀 Claude Code Worker Manager + ASR"
echo "========================================="
echo ""

ASR_SERVER_DIR="/Users/michael/projects/组件模块/audio-asr-suite/go/audio-asr-go"
ASR_LOG_FILE="./asr_server.log"
FASTAPI_PID_FILE="./fastapi.pid"
ASR_PID_FILE="./asr.pid"

cleanup() {
    echo ""
    echo "正在停止服务..."

    if [ -f "$FASTAPI_PID_FILE" ]; then
        FASTAPI_PID=$(cat "$FASTAPI_PID_FILE")
        if kill -0 "$FASTAPI_PID" 2>/dev/null; then
            echo "停止 FastAPI Server (PID: $FASTAPI_PID)"
            kill "$FASTAPI_PID"
        fi
        rm -f "$FASTAPI_PID_FILE"
    fi

    if [ -f "$ASR_PID_FILE" ]; then
        ASR_PID=$(cat "$ASR_PID_FILE")
        if kill -0 "$ASR_PID" 2>/dev/null; then
            echo "停止 Go ASR Server (PID: $ASR_PID)"
            kill "$ASR_PID"
        fi
        rm -f "$ASR_PID_FILE"
    fi

    echo "服务已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

if [ ! -d "$ASR_SERVER_DIR" ]; then
    echo "错误: Go ASR Server 目录不存在: $ASR_SERVER_DIR"
    exit 1
fi

echo "1. 启动 Go ASR Server (localhost:18080)..."
cd "$ASR_SERVER_DIR"
DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:?请设置 DASHSCOPE_API_KEY 环境变量}" \
    go run cmd/asr-server/main.go > "$ASR_LOG_FILE" 2>&1 &
ASR_PID=$!
echo "$ASR_PID" > "$ASR_PID_FILE"
echo "   Go ASR Server 已启动 (PID: $ASR_PID)"
echo "   日志: $ASR_LOG_FILE"
sleep 2

cd "$(dirname "$0")"

if ! curl -s http://localhost:18080/health > /dev/null 2>&1; then
    echo "警告: Go ASR Server 未正常启动，请检查日志"
fi

echo ""
echo "2. 启动 FastAPI Server (localhost:8000)..."
./venv/bin/python main.py &
FASTAPI_PID=$!
echo "$FASTAPI_PID" > "$FASTAPI_PID_FILE"
echo "   FastAPI Server 已启动 (PID: $FASTAPI_PID)"

echo ""
echo "========================================="
echo "✅ 所有服务已启动"
echo "========================================="
echo "FastAPI:      http://localhost:8000"
echo "Go ASR Server: http://localhost:18080"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

wait $FASTAPI_PID
