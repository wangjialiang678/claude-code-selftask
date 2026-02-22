# Claude Code 自动任务系统 - 项目配置

本项目用于测试多 Claude Code 并行工作流（基于胡渊鸣《我给 10 个 Claude Code 打工》）。

---

## 任务生命周期（"干活"逻辑）

当 Claude Code 在 worktree 中启动时，遵循以下流程：

### 1. 领取任务

从 `data/dev-tasks.json` 原子读取第一个 `pending` 任务：

```bash
# 检查任务池
cat data/dev-tasks.json

# 任务格式示例
{
  "id": "task-001",
  "description": "实现用户认证功能",
  "status": "pending"
}
```

**如果没有任务，直接退出。**

---

### 2. 标记任务状态

将任务状态改为 `working`：

```bash
# 使用 jq 原子更新
jq '.tasks |= map(if .id == "task-001" then .status = "working" else . end)' \
   data/dev-tasks.json > data/dev-tasks.json.tmp
mv data/dev-tasks.json.tmp data/dev-tasks.json
```

---

### 3. 执行任务

根据任务描述，完成以下工作：

- 阅读相关代码
- 实现功能
- 编写测试（如果需要）
- 提交代码到当前 worktree 分支

**重要规则：**
- ✅ 只做任务描述的事情，不要过度设计
- ✅ 以"能跑起来"为第一目标
- ✅ 遵循 KISS 原则
- ❌ 不要添加任务外的功能

---

### 4. 提交代码

```bash
# 提交到当前 worktree 分支
git add .
git commit -m "完成任务: ${task_description}

任务 ID: ${task_id}

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### 5. 合并到主分支

```bash
# 拉取最新 main
git fetch origin main

# Rebase 到 main
git rebase origin/main

# 推送到远程
git push origin HEAD:main
```

**如果遇到冲突：**
- 尝试自动解决简单冲突
- 复杂冲突则标记任务为 `failed`，释放任务

---

### 6. 运行测试（如果有）

```bash
# 如果项目有测试脚本
npm test || pytest || go test ./... || echo "无测试"
```

**测试失败处理：**
- 尝试修复一次
- 仍失败则标记 `failed`，释放任务

---

### 7. 标记任务完成

```bash
# 更新任务状态为 done
jq '.tasks |= map(if .id == "task-001" then .status = "done" else . end)' \
   data/dev-tasks.json > data/dev-tasks.json.tmp
mv data/dev-tasks.json.tmp data/dev-tasks.json
```

---

### 8. 记录经验（重要！）

在 `PROGRESS.md` 中追加本次任务的经验：

```markdown
## 任务: task-001 - 实现用户认证

**完成时间:** 2026-02-23
**遇到的问题:**
- JWT token 签名方式需要用 HS256
- 环境变量 SECRET_KEY 需要在 .env 中配置

**经验教训:**
- 同样的问题不要犯两次！下次直接用 HS256

**代码位置:**
- src/auth/jwt.py
```

---

### 9. 退出

```bash
# 干活完成，退出让外部 Manager 重启
exit 0
```

**注意：** 不要无限循环！完成一个任务就退出，让 Worker Manager 重新分配任务。

---

## 错误处理规则

| 错误类型 | 处理方式 |
|---------|---------|
| 任务池为空 | 直接退出（exit 0） |
| Git 冲突 | 尝试解决，失败则 `status=failed`，退出 |
| 测试失败 | 修复一次，仍失败则 `status=failed`，退出 |
| 代码错误 | 修复一次，仍失败则 `status=failed`，退出 |

**永远不要死循环！** 遇到问题就释放任务并退出。

---

## 项目特定约定

### 文件路径
- 任务池：`data/dev-tasks.json`
- 进度记录：`PROGRESS.md`
- 项目根目录：`/Users/michael/projects/claude-code-selftask`

### Git 分支命名
- 主分支：`main`
- 任务分支：`task/{task-id}`（由 Worker Manager 创建）

### 环境变量
- API Key 等敏感信息放在 `data/.env`
- 不要提交 `.env` 到 git

---

## 与全局 CLAUDE.md 的区别

**全局配置** (`~/.claude/CLAUDE.md` 或 `/Users/michael/projects/CLAUDE.md`):
- 适用于所有项目的通用规则
- 编码风格、安全规范、通用工作流

**本项目配置** (`~/projects/claude-code-selftask/CLAUDE.md`):
- 仅适用于本项目的"干活"逻辑
- 任务生命周期、错误处理、Ralph Loop 规则

**优先级：** 项目级配置 > 全局配置

---

## 测试用例

### 简单任务示例

```json
{
  "id": "task-hello",
  "description": "创建 hello.txt 文件，内容为 'Hello from Worker'",
  "status": "pending"
}
```

**预期行为：**
1. 创建文件 `hello.txt`
2. 写入内容
3. Git commit + push
4. 标记任务为 `done`
5. 退出

---

**记住：这个 CLAUDE.md 只在 `~/projects/claude-code-selftask` 项目中生效！**
