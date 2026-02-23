# 进度与经验记录

本文件记录每个任务的执行情况和经验教训。

**重要：** AI 在完成任务后必须在此记录经验，避免重复犯错。

---

## 项目初始化

**时间:** 2026-02-23
**事件:** 项目创建，迁移到独立目录

**配置:**
- Claude Code: 2.1.50 (原生 worktree 支持)
- Web Manager: FastAPI
- 远程访问: Cloudflare Tunnel

**目录结构:**
- 任务池: `data/dev-tasks.json`
- 项目配置: `CLAUDE.md`（仅本项目生效）
- 全局配置: `/Users/michael/projects/CLAUDE.md`（通用规则）

---

## 任务记录格式

```markdown
## 任务: ${task_id} - ${description}

**完成时间:** YYYY-MM-DD HH:MM
**执行时长:** X 分钟
**Worker ID:** worker-N

**遇到的问题:**
- 问题 1
- 问题 2

**解决方案:**
- 方案 1
- 方案 2

**经验教训:**
- 教训 1（下次注意）
- 教训 2（同样的错误不要犯两次）

**修改的文件:**
- path/to/file1.py:42-56
- path/to/file2.js:10-20
```

---

## 任务: task-20260223-143834-320e61cc - 整理 worktree-worker 目录结构

**完成时间:** 2026-02-23
**Worker ID:** worker-test

**工作内容:**
- 检查 worktree-worker 目录位置（已在正确位置 `worktrees/` 下）
- 修复 `.gitignore`：`.worktrees/` → `worktrees/`（名称不匹配实际目录）
- 更新 `README.md` 项目结构，补充 `worktrees/` 和 `tests/` 目录
- 确认 `worker_manager.py` 路径配置正确，无需修改

**经验教训:**
- `.gitignore` 中的路径必须和实际目录名完全一致
- worktree 目录结构变更后需同步更新项目文档

**修改的文件:**
- .gitignore
- README.md
- PROGRESS.md

---

## 待办事项

- [ ] 测试第一个 Worker 运行
- [ ] 验证 Ralph Loop 自动循环
- [ ] 测试多 Worker 并行
- [ ] 集成 FunASR 语音输入

---
