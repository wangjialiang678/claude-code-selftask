#!/usr/bin/env python3
"""
多 Worker 并行测试脚本

测试场景：
- 3 个 Worker 并行执行
- 5 个测试任务
- 统计成功率、平均耗时、并发效率
"""
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# 添加 worktree-manager 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "worktree-manager"))

from worker_manager import WorkerManager, TaskQueue


class TestMonitor:
    """测试监控器"""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        """开始监控"""
        self.start_time = time.time()
        print("=" * 60)
        print("多 Worker 并行测试")
        print("=" * 60)
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    def print_status(self):
        """打印当前状态"""
        queue = TaskQueue.load()
        tasks = queue["tasks"]

        total = len(tasks)
        pending = sum(1 for t in tasks if t.get("status") == "pending")
        working = sum(1 for t in tasks if t.get("status") == "working")
        done = sum(1 for t in tasks if t.get("status") == "done")
        failed = sum(1 for t in tasks if t.get("status") == "failed")

        elapsed = time.time() - self.start_time
        print(f"\n[{elapsed:.1f}s] 任务状态: 总数={total}, 待处理={pending}, 工作中={working}, 完成={done}, 失败={failed}")

        # 显示工作中的任务
        if working > 0:
            print("  工作中的任务:")
            for t in tasks:
                if t.get("status") == "working":
                    print(f"    - {t['id']} (Worker: {t.get('worker_id', 'N/A')})")

        return pending + working == 0  # 所有任务完成

    def calculate_statistics(self):
        """计算统计数据"""
        self.end_time = time.time()
        queue = TaskQueue.load()
        tasks = queue["tasks"]

        total = len(tasks)
        done = [t for t in tasks if t.get("status") == "done"]
        failed = [t for t in tasks if t.get("status") == "failed"]

        done_count = len(done)
        failed_count = len(failed)
        success_rate = (done_count / total * 100) if total > 0 else 0

        # 计算平均耗时（秒）
        durations = []
        for t in done:
            if "started_at" in t and "completed_at" in t:
                start = datetime.fromisoformat(t["started_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(t["completed_at"].replace("Z", "+00:00"))
                duration = (end - start).total_seconds()
                durations.append(duration)

        avg_duration = sum(durations) / len(durations) if durations else 0
        total_elapsed = self.end_time - self.start_time

        # 计算并发效率
        # 理论耗时 = 总任务数 * 平均单任务耗时
        # 实际耗时 = 总测试耗时
        # 并发效率 = 理论耗时 / 实际耗时
        theoretical_time = total * avg_duration if avg_duration > 0 else 0
        efficiency = (theoretical_time / total_elapsed * 100) if total_elapsed > 0 else 0

        return {
            "total": total,
            "done": done_count,
            "failed": failed_count,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "total_elapsed": total_elapsed,
            "theoretical_time": theoretical_time,
            "efficiency": efficiency,
            "durations": durations
        }

    def print_report(self, stats):
        """打印测试报告"""
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print(f"总任务数:   {stats['total']}")
        print(f"成功任务:   {stats['done']}")
        print(f"失败任务:   {stats['failed']}")
        print(f"成功率:     {stats['success_rate']:.1f}%")
        print()
        print(f"平均耗时:   {stats['avg_duration']:.1f}s/任务")
        print(f"总耗时:     {stats['total_elapsed']:.1f}s")
        print(f"理论耗时:   {stats['theoretical_time']:.1f}s（单线程）")
        print(f"并发效率:   {stats['efficiency']:.1f}%")
        print()

        if stats['durations']:
            print("各任务耗时:")
            for i, duration in enumerate(stats['durations'], 1):
                print(f"  任务 {i}: {duration:.1f}s")
            print()

        # 评价
        if stats['success_rate'] == 100:
            print("✅ 测试成功！所有任务均已完成。")
        else:
            print(f"⚠️  测试部分失败，{stats['failed']} 个任务未完成。")

        if stats['efficiency'] >= 150:
            print("✅ 并发效率优秀（>150%）")
        elif stats['efficiency'] >= 100:
            print("⚠️  并发效率一般（100-150%）")
        else:
            print("❌ 并发效率低（<100%），可能存在性能问题")

        print("=" * 60)


async def monitor_loop(monitor, timeout=300):
    """
    监控循环
    每 5 秒打印一次状态，所有任务完成或超时后退出
    """
    start = time.time()
    while True:
        # 检查状态
        all_done = monitor.print_status()

        if all_done:
            print("\n✅ 所有任务已完成！")
            break

        # 检查超时
        elapsed = time.time() - start
        if elapsed > timeout:
            print(f"\n⚠️  超时（{timeout}s），停止测试。")
            break

        # 等待 5 秒
        await asyncio.sleep(5)


async def main():
    """主测试函数"""
    monitor = TestMonitor()
    monitor.start()

    # 验证任务队列
    queue = TaskQueue.load()
    print(f"任务队列: {len(queue['tasks'])} 个任务")
    for task in queue["tasks"]:
        print(f"  - {task['id']}: {task['status']}")
    print()

    # 启动 Worker Manager（3 个 Worker）
    print("启动 3 个 Worker...")
    manager = WorkerManager(max_workers=3)

    # 并行运行 Worker 和监控
    try:
        await asyncio.gather(
            manager.start_all(),
            monitor_loop(monitor, timeout=300)
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断测试")

    # 计算并输出统计
    print("\n计算统计数据...")
    stats = monitor.calculate_statistics()
    monitor.print_report(stats)


if __name__ == "__main__":
    asyncio.run(main())
