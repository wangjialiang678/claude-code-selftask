# Claude Code 自动任务系统

> 基于胡渊鸣《我给 10 个 Claude Code 打工》的复刻实现

## 项目简介

多 Claude Code 实例并行工作流系统，支持：
- ✅ 原生 Git Worktree 并行（Claude Code 2.1.50+）
- ✅ Ralph Loop 自动循环（干活→退出→重启）
- ✅ Web 管理界面（FastAPI + PWA）
- ✅ 移动端访问（Cloudflare Tunnel）
- ✅ 语音输入（FunASR）

## 快速开始

### 1. 启动 Web Manager

```bash
cd worktree-manager
source venv/bin/activate
python main.py
```

访问：`http://localhost:8000`

### 2. 启动 Cloudflare Tunnel（移动端访问）

```bash
cloudflared tunnel --url http://localhost:8000
```

获取公网地址（如 `https://xxx.trycloudflare.com`）

### 3. 添加任务

编辑 `data/dev-tasks.json`：

```json
{
  "tasks": [
    {
      "id": "task-001",
      "description": "实现用户认证功能",
      "status": "pending"
    }
  ]
}
```

### 4. 启动 Worker

Worker 会自动：
1. 领取 `pending` 任务
2. 在独立 worktree 中执行
3. 完成后合并到 main
4. 标记任务 `done`
5. 退出并等待下一个任务

## 项目结构

```
claude-code-selftask/
├─ worktree-manager/       # Web 管理服务
│   ├─ main.py            # FastAPI 主服务
│   ├─ worker_manager.py  # Worker 生命周期管理
│   ├─ static/            # 前端 PWA
│   └─ venv/              # Python 虚拟环境
│
├─ data/                   # 运行时数据
│   ├─ dev-tasks.json     # 任务队列
│   └─ .env               # 环境变量（不提交）
│
├─ docs/                   # 文档
│   └─ research/          # 调研报告
│
├─ .claude/                # Claude Code 配置（如需要）
│
├─ CLAUDE.md              # 项目级"干活"逻辑
├─ PROGRESS.md            # AI 经验记录
└─ README.md              # 本文件
```

## 核心功能

### 1. 原生 Worktree 支持

使用 Claude Code 2.1.50+ 的 `--worktree` 参数：

```bash
claude -w -p "干活：实现用户认证，干完请退出"
```

Claude Code 自动管理 worktree 创建/销毁。

### 2. Ralph Loop

```python
while True:
    task = claim_task()
    if not task:
        break

    run_claude_code(f"干活：{task['description']}")

    if task_completed():
        mark_done(task)
```

### 3. Web 管理界面

- 任务列表（pending/working/done）
- Worker 状态监控
- 实时日志（WebSocket）
- 语音输入（可选）

## 配置说明

### CLAUDE.md（项目级）

定义了"干活"逻辑，包括：
- 任务领取流程
- Git 操作规范
- 错误处理规则
- 经验记录要求

### 环境变量（data/.env）

```bash
# FunASR API Key
DASHSCOPE_API_KEY=sk-xxx

# Web Manager
WEB_PORT=8000
WORKERS_MAX=5
```

## 开发计划

- [x] 升级 Claude Code 到 2.1.50
- [x] 配置 Cloudflare Tunnel
- [x] 创建基础 Web Manager
- [ ] 实现 Worker Manager
- [ ] 实现 Ralph Loop
- [ ] 添加实时日志
- [ ] 集成 FunASR 语音输入
- [ ] 添加 Plan Mode 触发

## 相关文档

- [调研报告](docs/multi-cc-worktree-system-20260222.md)
- [修正说明](docs/multi-cc-worktree-system-corrections-20260222.md)
- [原文章]：胡渊鸣《我给 10 个 Claude Code 打工》

## License

MIT
