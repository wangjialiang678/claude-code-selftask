#!/usr/bin/env python3
"""
自动化测试运行器
用于验证 Worker 功能是否正常
"""
import json
import subprocess
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TESTS_DIR = PROJECT_ROOT / "tests"


def load_test_tasks():
    """加载测试任务"""
    with open(TESTS_DIR / "test_tasks.json") as f:
        return json.load(f)


def load_task_queue():
    """加载任务队列"""
    with open(DATA_DIR / "dev-tasks.json") as f:
        return json.load(f)


def save_task_queue(queue):
    """保存任务队列"""
    with open(DATA_DIR / "dev-tasks.json", "w") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def add_test_task(task):
    """添加测试任务到队列"""
    queue = load_task_queue()
    queue["tasks"].append({
        "id": task["id"],
        "description": task["description"],
        "status": "pending",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    })
    save_task_queue(queue)
    print(f"✓ 已添加测试任务: {task['id']}")


def validate_task(task):
    """验证任务是否完成"""
    print(f"\n验证任务: {task['id']}")

    # 检查预期文件
    if "expected_files" in task:
        for file in task["expected_files"]:
            file_path = PROJECT_ROOT / file
            if not file_path.exists():
                print(f"  ✗ 文件不存在: {file}")
                return False
            print(f"  ✓ 文件存在: {file}")

    # 运行验证命令
    if "validation" in task:
        try:
            result = subprocess.run(
                task["validation"],
                shell=True,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  ✓ 验证通过")
                return True
            else:
                print(f"  ✗ 验证失败: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"  ✗ 验证超时")
            return False
        except Exception as e:
            print(f"  ✗ 验证出错: {e}")
            return False

    return True


def run_level(level_name, tasks):
    """运行一个级别的测试"""
    print(f"\n{'='*60}")
    print(f"运行测试级别: {level_name}")
    print(f"{'='*60}")

    for task in tasks:
        print(f"\n[任务] {task['id']}: {task['description']}")

        # 添加到任务队列
        add_test_task(task)

        # 等待任务完成（这里暂时手动检查，后续集成 Worker）
        input("→ 按回车继续验证...")

        # 验证任务
        if validate_task(task):
            print(f"✓ 任务 {task['id']} 验证通过")
        else:
            print(f"✗ 任务 {task['id']} 验证失败")
            return False

    print(f"\n✓ 级别 {level_name} 全部通过")
    return True


def main():
    """主函数"""
    print("Claude Code 自动任务系统 - 测试运行器")
    print("="*60)

    # 加载测试任务
    test_data = load_test_tasks()

    # 选择测试级别
    print("\n可用测试级别:")
    levels = list(test_data["tasks"].keys())
    for i, level in enumerate(levels, 1):
        print(f"  {i}. {level}")

    choice = input("\n选择测试级别 (1-{}, 或 'all'): ".format(len(levels)))

    if choice == "all":
        # 运行所有级别
        for level_name in levels:
            if not run_level(level_name, test_data["tasks"][level_name]):
                print(f"\n✗ 测试在级别 {level_name} 失败")
                sys.exit(1)
        print("\n✓ 所有测试通过！")
    else:
        # 运行单个级别
        try:
            idx = int(choice) - 1
            level_name = levels[idx]
            if run_level(level_name, test_data["tasks"][level_name]):
                print("\n✓ 测试通过！")
            else:
                print("\n✗ 测试失败")
                sys.exit(1)
        except (ValueError, IndexError):
            print("无效的选择")
            sys.exit(1)


if __name__ == "__main__":
    main()
