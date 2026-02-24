#!/usr/bin/env python3
"""
Claude Code Worktree Manager - Web 管理服务
基于 FastAPI + 原生 worktree 支持
"""
import asyncio
import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timezone
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import httpx

# 导入 worker_manager
from worker_manager import TaskQueue

app = FastAPI(title="Claude Code Worktree Manager")

# 数据目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TASKS_FILE = DATA_DIR / "dev-tasks.json"
STATIC_DIR = Path(__file__).parent / "static"

# 确保数据目录存在
DATA_DIR.mkdir(exist_ok=True)
if not TASKS_FILE.exists():
    TASKS_FILE.write_text(json.dumps({"tasks": []}, indent=2))

# 全局状态
active_connections: List[WebSocket] = []
worker_status: Dict[str, Dict] = {}

# 请求模型
class TaskCreate(BaseModel):
    description: str

class TaskUpdate(BaseModel):
    status: str  # pending, working, done, failed


# WebSocket 广播函数
async def broadcast_log(message: Dict):
    """广播日志到所有连接的 WebSocket 客户端"""
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected.append(connection)

    # 清理断开的连接
    for conn in disconnected:
        active_connections.remove(conn)


@app.get("/")
async def root():
    """主页 - 返回静态 HTML"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        # 如果静态文件不存在，返回简单的欢迎页面
        return {
            "message": "Claude Code Worktree Manager API",
            "endpoints": {
                "status": "/api/status",
                "tasks": "/api/tasks",
                "websocket": "/ws"
            }
        }


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    queue = TaskQueue.load()
    tasks = queue.get("tasks", [])

    pending_count = sum(1 for t in tasks if t.get("status") == "pending")
    working_count = sum(1 for t in tasks if t.get("status") == "working")
    done_count = sum(1 for t in tasks if t.get("status") == "done")

    return {
        "claude_version": "2.1.50",
        "worktree_native": True,
        "workers": len(worker_status),
        "max_workers": 5,
        "tasks": {
            "total": len(tasks),
            "pending": pending_count,
            "working": working_count,
            "done": done_count
        }
    }


@app.get("/api/tasks")
async def list_tasks():
    """获取任务列表"""
    queue = TaskQueue.load()
    return {"tasks": queue.get("tasks", [])}


@app.post("/api/tasks")
async def create_task(task: TaskCreate):
    """创建新任务"""
    queue = TaskQueue.load()

    # 生成任务 ID
    task_id = f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8]}"

    new_task = {
        "id": task_id,
        "description": task.description,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    if "tasks" not in queue:
        queue["tasks"] = []

    queue["tasks"].append(new_task)
    TaskQueue.save(queue)

    # 广播任务创建事件
    await broadcast_log({
        "type": "task_created",
        "task": new_task,
        "timestamp": datetime.now().isoformat()
    })

    return {"success": True, "task": new_task}


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, task_update: TaskUpdate):
    """更新任务状态"""
    queue = TaskQueue.load()

    task_found = False
    for task in queue.get("tasks", []):
        if task["id"] == task_id:
            task["status"] = task_update.status

            if task_update.status == "done" or task_update.status == "failed":
                task["completed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            task_found = True
            break

    if not task_found:
        raise HTTPException(status_code=404, detail="Task not found")

    TaskQueue.save(queue)

    # 广播任务更新事件
    await broadcast_log({
        "type": "task_updated",
        "task_id": task_id,
        "status": task_update.status,
        "timestamp": datetime.now().isoformat()
    })

    return {"success": True}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    queue = TaskQueue.load()

    original_count = len(queue.get("tasks", []))
    queue["tasks"] = [t for t in queue.get("tasks", []) if t["id"] != task_id]

    if len(queue["tasks"]) == original_count:
        raise HTTPException(status_code=404, detail="Task not found")

    TaskQueue.save(queue)

    # 广播任务删除事件
    await broadcast_log({
        "type": "task_deleted",
        "task_id": task_id,
        "timestamp": datetime.now().isoformat()
    })

    return {"success": True}


@app.get("/api/workers")
async def list_workers():
    """列出所有 worker 状态"""
    return {"workers": list(worker_status.values())}


# ASR 代理端点（避免 CORS 问题）
ASR_SERVER_URL = "http://localhost:18080"

@app.post("/api/asr/upload")
async def proxy_asr_upload(file: UploadFile = File(...)):
    """代理 ASR 音频上传请求"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (file.filename, await file.read(), file.content_type)}
            response = await client.post(f"{ASR_SERVER_URL}/v1/asr/recorded", files=files)
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(
            content={"error": str(e), "ok": False},
            status_code=500
        )


@app.get("/api/asr/tasks/{task_id}")
async def proxy_asr_task(task_id: str):
    """代理 ASR 任务查询请求"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ASR_SERVER_URL}/v1/asr/tasks/{task_id}")
            return JSONResponse(content=response.json(), status_code=response.status_code)
    except Exception as e:
        return JSONResponse(
            content={"error": str(e), "ok": False},
            status_code=500
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接 - 实时日志和状态更新"""
    await websocket.accept()
    active_connections.append(websocket)

    # 发送欢迎消息
    await websocket.send_json({
        "type": "connected",
        "message": "已连接到 Worker Manager",
        "timestamp": datetime.now().isoformat()
    })

    try:
        while True:
            # 接收客户端消息（心跳等）
            data = await websocket.receive_text()

            # 可以处理客户端发送的命令
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        active_connections.remove(websocket)


# 挂载静态文件（必须在路由定义之后）
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Claude Code Worktree Manager 启动中...")
    print("=" * 60)
    print(f"📍 本地访问: http://localhost:8000")
    print(f"📁 静态文件: {STATIC_DIR}")
    print(f"📁 任务文件: {TASKS_FILE}")
    print(f"📱 WebSocket: ws://localhost:8000/ws")
    print("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
