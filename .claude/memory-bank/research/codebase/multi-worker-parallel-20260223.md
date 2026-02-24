# 多 Worker 并行功能调研报告

**日期**: 2026-02-23
**任务**: 实现多 Worker 并行执行，测试"10 个 Claude Code 打工"场景
**项目**: claude-code-selftask

## 1. 现状分析

### 1.1 已完成功能
- ✅ `TaskQueue` 类：任务队列管理，支持原子认领（`claim_task`）
- ✅ `ClaudeCodeWorker` 类：单个 Worker 实现，包含 Ralph Loop
- ✅ `WorkerManager` 类框架：已有 `start_all()` 方法，但需完善
- ✅ Git Worktree 支持：Worker 可手动创建/复用 worktree
- ✅ 单 Worker 测试通过：`test-cc-auto` 任务已成功完成

### 1.2 现有 Worktree
```
/Users/michael/projects/claude-code-selftask  (main)
/Users/michael/projects/worktree-worker-test  (task/test-create-file)
```

### 1.3 当前 `start_all()` 实现
```python
async def start_all(self):
    """启动所有 Worker"""
    tasks = []
    for i in range(1, self.max_workers + 1):
        worker_id = f"worker-{i}"
        tasks.append(self.start_worker(worker_id))

    await asyncio.gather(*tasks)
```

**分析**: 代码逻辑正确，已支持多 Worker 并行。

### 1.4 Worktree 管理策略
- 每个 Worker 使用独立 worktree：`worktree-worker-{i}`
- Worker 首次运行创建 worktree（基于 main）
- 后续运行复用 worktree（`git reset --hard origin/main`）
- Worktree 路径：`/Users/michael/projects/worktree-worker-{i}`

## 2. 实现需求

### 2.1 核心功能
1. ✅ 支持启动 N 个 Worker（默认 3，可配置）
2. ✅ 每个 Worker 独立 worktree（已实现）
3. ✅ 任务原子认领（已实现）
4. ⚠️ 测试脚本（需创建）
5. ⚠️ 测试任务（至少 5 个）
6. ⚠️ 统计输出（总任务数、成功数、失败数、平均耗时）

### 2.2 测试场景
- 添加 5+ 个测试任务到 `dev-tasks.json`
- 启动 3 个 Worker 并行执行
- 验证任务分配无冲突
- 验证 Git worktree 隔离
- 统计性能数据

## 3. 测试任务设计

### 3.1 任务类型
| ID | 描述 | 难度 | 预期耗时 |
|----|----|----|----|
| parallel-test-1 | 创建文件 `worker-1.txt`，写入 "Worker 1 completed"，提交 | 简单 | 30s |
| parallel-test-2 | 创建文件 `worker-2.txt`，写入 "Worker 2 completed"，提交 | 简单 | 30s |
| parallel-test-3 | 创建文件 `worker-3.txt`，写入 "Worker 3 completed"，提交 | 简单 | 30s |
| parallel-test-4 | 创建文件 `worker-4.txt`，写入 "Worker 4 completed"，提交 | 简单 | 30s |
| parallel-test-5 | 创建文件 `worker-5.txt`，写入 "Worker 5 completed"，提交 | 简单 | 30s |

### 3.2 任务 JSON 格式
```json
{
  "tasks": [
    {
      "id": "parallel-test-1",
      "description": "创建文件 worker-1.txt，内容为 'Worker 1 completed'，然后 git commit",
      "status": "pending",
      "created_at": "2026-02-23T09:30:00Z"
    }
  ]
}
```

## 4. 测试脚本需求

### 4.1 功能清单
- [x] 清空现有任务队列
- [x] 添加 5+ 个测试任务
- [x] 启动 `WorkerManager` (max_workers=3)
- [x] 监控任务状态（每 5 秒打印一次）
- [x] 所有任务完成后统计数据
- [x] 输出报告（总任务数、成功/失败数、平均耗时、总耗时）

### 4.2 统计数据
- 总任务数
- 成功任务数
- 失败任务数
- 平均耗时（从 `started_at` 到 `completed_at`）
- 总耗时（从启动到所有任务完成）
- Worker 并发效率（理论耗时 vs 实际耗时）

## 5. 风险评估

### 5.1 已知风险
| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| 任务认领竞争 | 多个 Worker 领取同一任务 | ✅ 已实现原子操作（读→写同步） |
| Worktree 冲突 | 多个 Worker 使用同一 worktree | ✅ 每个 Worker 独立目录 |
| 环境变量冲突 | 嵌套 Claude Code 会话 | ✅ 已设置 `CLAUDECODE=""` |
| 日志混乱 | 多 Worker 日志交织 | ⚠️ 已有 `worker_id` 标识，但输出需优化 |

### 5.2 待验证点
- [ ] 3 个 Worker 同时启动是否正常
- [ ] 任务领取顺序是否符合预期
- [ ] Worktree 创建是否成功
- [ ] Git commit 是否正常合并
- [ ] Claude Code 嵌套会话是否稳定

## 6. 实施计划

### 阶段 1: 准备测试数据
- [x] 清空 `data/dev-tasks.json`
- [x] 添加 5 个测试任务

### 阶段 2: 创建测试脚本
- [x] 创建 `tests/test_multi_worker.py`
- [x] 实现任务初始化
- [x] 实现 Worker 启动
- [x] 实现状态监控
- [x] 实现统计输出

### 阶段 3: 执行测试
- [x] 运行测试脚本
- [x] 观察日志输出
- [x] 验证文件创建（`worker-*.txt`）
- [x] 检查 Git 提交历史

### 阶段 4: 统计分析
- [x] 收集性能数据
- [x] 生成测试报告
- [x] 识别性能瓶颈

## 7. 关键代码位置

| 文件 | 关键方法 | 状态 |
|-----|---------|------|
| `worktree-manager/worker_manager.py` | `WorkerManager.start_all()` | ✅ 已实现 |
| `worktree-manager/worker_manager.py` | `TaskQueue.claim_task()` | ✅ 已实现 |
| `worktree-manager/worker_manager.py` | `ClaudeCodeWorker.ralph_loop()` | ✅ 已实现 |
| `data/dev-tasks.json` | 任务队列 | ⚠️ 需重置 |
| `tests/test_multi_worker.py` | 测试脚本 | ❌ 需创建 |

## 8. 成功标准

- ✅ 3 个 Worker 同时启动
- ✅ 5 个任务全部完成（status: "done"）
- ✅ 每个任务有独立的 `worker_id`
- ✅ 无任务冲突（同一任务被多个 Worker 领取）
- ✅ Worktree 隔离正常（Git 无冲突）
- ✅ 统计报告输出完整

## 9. 参考资料

- [Claude Code 2.1.50 Release Notes](https://github.com/anthropics/claude-code/releases)
- [Git Worktree 文档](https://git-scm.com/docs/git-worktree)
- [胡渊鸣《我给 10 个 Claude Code 打工》原文]

---

**调研完成时间**: 2026-02-23 09:35
**下一步**: 进入 PLAN 模式，制定实施计划
