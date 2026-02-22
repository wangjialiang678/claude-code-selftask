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

## 待办事项

- [ ] 测试第一个 Worker 运行
- [ ] 验证 Ralph Loop 自动循环
- [ ] 测试多 Worker 并行
- [ ] 集成 FunASR 语音输入

---
