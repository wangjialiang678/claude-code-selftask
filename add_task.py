#!/usr/bin/env python3
"""
快速添加任务脚本
用法: python3 add_task.py "任务描述"
"""
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

def add_task(description: str):
    """添加新任务到队列"""
    tasks_file = Path(__file__).parent / "data" / "dev-tasks.json"

    # 加载现有任务
    with open(tasks_file) as f:
        queue = json.load(f)

    # 创建新任务
    task_id = f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    new_task = {
        "id": task_id,
        "description": description,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    # 添加到队列
    if "tasks" not in queue:
        queue["tasks"] = []
    queue["tasks"].append(new_task)

    # 保存
    with open(tasks_file, "w") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

    print(f"✅ 任务已添加:")
    print(f"   ID: {task_id}")
    print(f"   描述: {description}")
    print(f"   状态: pending")
    print(f"\n💡 启动 Worker 执行任务:")
    print(f"   cd worktree-manager && python3 worker_manager.py")

    return task_id

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 add_task.py '任务描述'")
        print("\n示例:")
        print("  python3 add_task.py '创建文件 test.txt，内容为 Hello'")
        print("  python3 add_task.py '实现用户登录功能'")
        sys.exit(1)

    description = " ".join(sys.argv[1:])
    add_task(description)
