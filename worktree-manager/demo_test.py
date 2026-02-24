#!/usr/bin/env python3
"""
演示测试 - 验证 Web 管理界面功能
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_api():
    print("=" * 60)
    print("测试 Worker Manager API")
    print("=" * 60)
    
    # 1. 测试状态端点
    print("\n1. 测试 GET /api/status")
    try:
        resp = requests.get(f"{BASE_URL}/api/status")
        print(f"   状态码: {resp.status_code}")
        print(f"   响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   错误: {e}")
        print("   提示: 请先启动服务器 (./start.sh)")
        return
    
    # 2. 测试任务列表
    print("\n2. 测试 GET /api/tasks")
    resp = requests.get(f"{BASE_URL}/api/tasks")
    print(f"   状态码: {resp.status_code}")
    data = resp.json()
    print(f"   任务数量: {len(data.get('tasks', []))}")
    
    # 3. 创建测试任务
    print("\n3. 测试 POST /api/tasks")
    task_data = {
        "description": "测试任务：创建文件 web-test.txt，内容为 'Web界面测试成功'"
    }
    resp = requests.post(f"{BASE_URL}/api/tasks", json=task_data)
    print(f"   状态码: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"   任务已创建: {result['task']['id']}")
        task_id = result['task']['id']
        
        # 4. 验证任务已添加
        print("\n4. 验证任务列表")
        resp = requests.get(f"{BASE_URL}/api/tasks")
        data = resp.json()
        print(f"   当前任务数: {len(data.get('tasks', []))}")
        
        # 找到刚创建的任务
        created_task = next((t for t in data['tasks'] if t['id'] == task_id), None)
        if created_task:
            print(f"   ✓ 找到任务: {created_task['description'][:50]}...")
            print(f"   状态: {created_task['status']}")
        
    print("\n" + "=" * 60)
    print("API 测试完成")
    print("=" * 60)
    print("\n请在浏览器中访问: http://localhost:8000")
    print("查看 Web 界面效果\n")

if __name__ == "__main__":
    test_api()
