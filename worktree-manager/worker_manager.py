#!/usr/bin/env python3
"""
Worker Manager - 管理多个 Claude Code Worker
基于 Claude Code 2.1.50+ 原生 worktree 支持
"""
import asyncio
import json
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, List, Callable
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TASKS_FILE = DATA_DIR / "dev-tasks.json"


class TaskQueue:
    """任务队列管理"""

    @staticmethod
    def load():
        """加载任务队列"""
        if not TASKS_FILE.exists():
            return {"tasks": []}
        with open(TASKS_FILE) as f:
            return json.load(f)

    @staticmethod
    def save(queue):
        """保存任务队列"""
        with open(TASKS_FILE, "w") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)

    @staticmethod
    def claim_task(worker_id: str) -> Optional[Dict]:
        """
        原子认领任务
        返回: 任务对象或 None
        """
        queue = TaskQueue.load()

        # 找到第一个 pending 任务
        task = None
        for t in queue["tasks"]:
            if t.get("status") == "pending":
                task = t
                break

        if not task:
            return None

        # 标记为 working
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
        """标记任务完成"""
        queue = TaskQueue.load()

        for t in queue["tasks"]:
            if t["id"] == task_id:
                t["status"] = "done" if success else "failed"
                t["completed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                break

        TaskQueue.save(queue)

    @staticmethod
    def release_task(task_id: str):
        """释放任务（失败时重新变为 pending）"""
        queue = TaskQueue.load()

        for t in queue["tasks"]:
            if t["id"] == task_id:
                t["status"] = "pending"
                if "worker_id" in t:
                    del t["worker_id"]
                if "started_at" in t:
                    del t["started_at"]
                break

        TaskQueue.save(queue)


class ClaudeCodeWorker:
    """
    Claude Code Worker
    使用 Claude Code 2.1.50+ 原生 worktree 支持
    """

    def __init__(self, worker_id: str, log_callback: Optional[Callable] = None):
        self.worker_id = worker_id
        self.log_callback = log_callback
        self.process: Optional[asyncio.subprocess.Process] = None
        self.current_task: Optional[Dict] = None

    def log(self, message: str, level: str = "info"):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{self.worker_id}] {message}"
        print(log_entry)

        if self.log_callback:
            self.log_callback({
                "worker_id": self.worker_id,
                "timestamp": timestamp,
                "level": level,
                "message": message,
                "task_id": self.current_task["id"] if self.current_task else None
            })

    async def run_claude_code(self, prompt: str) -> int:
        """
        运行 Claude Code（手动管理 worktree）
        返回: exit code
        """
        import os

        # 1. 创建 worktree
        worktree_name = f"worktree-{self.worker_id}"
        # 将 worktree 放在项目内的 worktrees 目录
        worktree_base = PROJECT_ROOT / "worktrees"
        worktree_base.mkdir(exist_ok=True)
        worktree_path = worktree_base / worktree_name

        self.log(f"创建 worktree: {worktree_name}")

        # 检查 worktree 是否已存在
        worktree_exists = worktree_path.exists()

        if not worktree_exists:
            # 创建新的 worktree（基于 main 创建新分支）
            branch_name = f"task/{self.current_task['id']}" if self.current_task else f"worker-{self.worker_id}"
            result = subprocess.run(
                ["git", "worktree", "add", "-b", branch_name, str(worktree_path), "main"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.log(f"创建 worktree 失败: {result.stderr}", "error")
                return 1
            self.log(f"Worktree 已创建: {worktree_path} (分支: {branch_name})")
        else:
            # Worktree 存在，拉取最新代码
            self.log(f"复用现有 worktree: {worktree_path}")
            result = subprocess.run(
                ["git", "fetch", "origin", "main"],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            result = subprocess.run(
                ["git", "reset", "--hard", "origin/main"],
                cwd=worktree_path,
                capture_output=True,
                text=True
            )

        # 2. 启动 Claude Code（非交互模式）
        self.log(f"启动 Claude Code...")

        cmd = [
            "claude",
            "-p", prompt,
            "--dangerously-skip-permissions",
            "--no-session-persistence",  # 关键：禁用会话持久化
            "--output-format", "text"  # 使用 text 更简单
        ]

        self.log(f"命令: {' '.join(cmd[:2])}...")

        # 创建环境变量副本，清空 CLAUDECODE 以允许嵌套会话
        env = os.environ.copy()
        env["CLAUDECODE"] = ""  # 设置为空字符串

        # 启动进程（在 worktree 目录中）
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=worktree_path,
            env=env
        )

        # 读取输出（text 格式）
        async def read_stream(stream, stream_name):
            while True:
                line = await stream.readline()
                if not line:
                    break

                text = line.decode().strip()
                if text:
                    # 直接记录文本输出
                    self.log(f"[CC-{stream_name}] {text[:200]}")

        # 并行读取 stdout 和 stderr
        await asyncio.gather(
            read_stream(self.process.stdout, "OUT"),
            read_stream(self.process.stderr, "ERR")
        )

        # 等待进程结束
        exit_code = await self.process.wait()
        self.log(f"Claude Code 退出，exit code: {exit_code}")

        return exit_code

    async def ralph_loop(self):
        """
        Ralph Loop: 自动循环干活
        领任务 → 启动 CC → 等待完成 → 标记 done → 重启
        """
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

            self.current_task = task
            self.log(f"领取任务: {task['id']} - {task['description']}")

            # 2. 构建 prompt
            prompt = f"""干活：{task['description']}

任务 ID: {task['id']}

请严格按照 CLAUDE.md 中的流程执行：
1. 完成任务描述的工作
2. Git commit
3. 更新 data/dev-tasks.json 标记为 done
4. 退出

干完请退出 (exit)
"""

            # 3. 启动 Claude Code
            try:
                exit_code = await self.run_claude_code(prompt)

                # 4. 检查结果
                if exit_code == 0:
                    self.log(f"任务 {task['id']} 完成")
                    TaskQueue.complete_task(task["id"], success=True)
                else:
                    self.log(f"任务 {task['id']} 失败 (exit code {exit_code})", "error")
                    TaskQueue.complete_task(task["id"], success=False)

            except Exception as e:
                self.log(f"执行任务出错: {e}", "error")
                TaskQueue.release_task(task["id"])

            finally:
                self.current_task = None

            # 5. 短暂休眠后继续下一个任务
            await asyncio.sleep(2)


class WorkerManager:
    """Worker 管理器"""

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.workers: List[ClaudeCodeWorker] = []

    def log_callback(self, log_entry: Dict):
        """全局日志回调"""
        # TODO: 推送到 WebSocket
        pass

    async def start_worker(self, worker_id: str):
        """启动一个 Worker"""
        worker = ClaudeCodeWorker(worker_id, self.log_callback)
        self.workers.append(worker)

        print(f"启动 Worker: {worker_id}")
        await worker.ralph_loop()

    async def start_all(self):
        """启动所有 Worker"""
        tasks = []
        for i in range(1, self.max_workers + 1):
            worker_id = f"worker-{i}"
            tasks.append(self.start_worker(worker_id))

        await asyncio.gather(*tasks)


async def main():
    """主函数 - 用于测试"""
    print("=" * 60)
    print("Claude Code Worker Manager - 测试模式")
    print("=" * 60)

    # 启动单个 Worker 进行测试
    worker = ClaudeCodeWorker("worker-test")
    await worker.ralph_loop()


if __name__ == "__main__":
    asyncio.run(main())
