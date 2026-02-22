#!/usr/bin/env python3
"""
Claude Code Worktree Manager - Web 管理服务
基于 FastAPI + 原生 worktree 支持
"""
import asyncio
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI(title="Claude Code Worktree Manager")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 全局状态
workers = {}
active_connections: List[WebSocket] = []


@app.get("/")
async def root():
    """主页"""
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Code Manager</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            color: #00d4aa;
            margin-bottom: 30px;
            font-size: 2em;
        }
        .status {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .status h2 {
            color: #00d4aa;
            font-size: 1.2em;
            margin-bottom: 15px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .info-item {
            background: #0a0a0a;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #2a2a2a;
        }
        .info-label {
            color: #888;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        .info-value {
            color: #fff;
            font-size: 1.3em;
            font-weight: 600;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .badge-success { background: #00d4aa; color: #000; }
        .badge-warning { background: #ffaa00; color: #000; }
        .footer {
            margin-top: 40px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Claude Code Worktree Manager</h1>

        <div class="status">
            <h2>系统状态</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Claude Code 版本</div>
                    <div class="info-value">2.1.50</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Worktree 支持</div>
                    <div class="info-value">
                        <span class="badge badge-success">✓ 原生支持</span>
                    </div>
                </div>
                <div class="info-item">
                    <div class="info-label">运行中 Worker</div>
                    <div class="info-value">0 / 5</div>
                </div>
                <div class="info-item">
                    <div class="info-label">待处理任务</div>
                    <div class="info-value">0</div>
                </div>
            </div>
        </div>

        <div class="status">
            <h2>📱 移动端访问</h2>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">本地地址</div>
                    <div class="info-value" style="font-size: 1em;">
                        http://localhost:8000
                    </div>
                </div>
                <div class="info-item">
                    <div class="info-label">Cloudflare Tunnel</div>
                    <div class="info-value">
                        <span class="badge badge-warning">启动中...</span>
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>基于胡渊鸣《我给 10 个 Claude Code 打工》复刻</p>
            <p>Powered by FastAPI + Claude Code 2.1.50 原生 Worktree</p>
        </div>
    </div>
</body>
</html>
    """)


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    return {
        "claude_version": "2.1.50",
        "worktree_native": True,
        "workers": len(workers),
        "max_workers": 5,
        "pending_tasks": 0
    }


@app.get("/api/workers")
async def list_workers():
    """列出所有 worker"""
    return {"workers": list(workers.values())}


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """实时日志推送"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for now
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Claude Code Worktree Manager 启动中...")
    print("=" * 60)
    print(f"📍 本地访问: http://localhost:8000")
    print(f"📱 Cloudflare Tunnel 将在启动后显示公网地址")
    print("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
