#!/usr/bin/env python3
"""
简化版 Worker - 直接执行任务（不用 Claude Code）
用于验证 Worker 循环逻辑是否正常工作
"""
import asyncio
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TASKS_FILE = DATA_DIR / "dev-tasks.json"


class TaskQueue:
    """任务队列管理"""

    @staticmethod
    def load():
        if not TASKS_FILE.exists():
            return {"tasks": []}
        with open(TASKS_FILE) as f:
            return json.load(f)

    @staticmethod
    def save(queue):
        with open(TASKS_FILE, "w") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)

    @staticmethod
    def claim_task(worker_id: str):
        queue = TaskQueue.load()

        task = None
        for t in queue["tasks"]:
            if t.get("status") == "pending":
                task = t
                break

        if not task:
            return None

        for t in queue["tasks"]:
            if t["id"] == task["id"]:
                t["status"] = "working"
                t["worker_id"] = worker_id
                t["started_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                break

        TaskQueue.save(queue)
        return task

    @staticmethod
    def complete_task(task_id: str, success: bool = True):
        queue = TaskQueue.load()

        for t in queue["tasks"]:
            if t["id"] == task_id:
                t["status"] = "done" if success else "failed"
                t["completed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                break

        TaskQueue.save(queue)


class SimpleWorker:
    """简化版 Worker - 直接执行任务"""

    def __init__(self, worker_id: str):
        self.worker_id = worker_id

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.worker_id}] {message}")

    async def execute_task(self, task):
        """直接执行任务"""
        self.log(f"执行任务: {task['description']}")

        # 这里直接解析任务描述并执行
        # 示例: "创建文件 test-output.txt，内容为 'Test successful from 2026-02-23'"
        description = task['description']

        if "创建文件" in description:
            # 提取文件名和内容
            parts = description.split("，")
            filename = parts[0].replace("创建文件 ", "").strip()
            content = parts[1].replace("内容为 ", "").strip().strip("'\"")

            filepath = PROJECT_ROOT / filename
            self.log(f"创建文件: {filepath}")
            filepath.write_text(content + "\n")

            # Git commit
            self.log("提交到 Git...")
            subprocess.run(
                ["git", "add", filename],
                cwd=PROJECT_ROOT,
                check=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"完成任务: {task['id']}"],
                cwd=PROJECT_ROOT
            )

            return True
        else:
            self.log(f"不支持的任务类型")
            return False

    async def ralph_loop(self):
        """Ralph Loop"""
        self.log("Ralph Loop 启动")

        loop_count = 0
        while True:
            loop_count += 1
            self.log(f"=== 循环 #{loop_count} ===")

            # 1. 领取任务
            self.log("尝试领取任务...")
            task = TaskQueue.claim_task(self.worker_id)

            if not task:
                self.log("无任务，休眠 10 秒...")
                await asyncio.sleep(10)
                continue

            self.log(f"领取任务: {task['id']} - {task['description']}")

            # 2. 执行任务
            try:
                success = await self.execute_task(task)

                if success:
                    self.log(f"任务 {task['id']} 完成")
                    TaskQueue.complete_task(task["id"], success=True)
                else:
                    self.log(f"任务 {task['id']} 失败", )
                    TaskQueue.complete_task(task["id"], success=False)

            except Exception as e:
                self.log(f"执行任务出错: {e}")
                TaskQueue.complete_task(task["id"], success=False)

            # 3. 短暂休眠后继续
            await asyncio.sleep(2)


async def main():
    print("=" * 60)
    print("Simple Worker - 测试模式")
    print("=" * 60)

    worker = SimpleWorker("simple-test")
    await worker.ralph_loop()


if __name__ == "__main__":
    asyncio.run(main())
