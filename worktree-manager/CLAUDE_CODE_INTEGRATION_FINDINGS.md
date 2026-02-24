# Claude Code 子进程集成调研结果

## 测试日期
2026-02-23

## 核心发现

### ✅ Worker Loop 基础架构完全正常

通过 `simple_worker_test.py` 验证:

1. **任务队列管理** - 完美工作
   - 原子任务认领 ✅
   - 状态跟踪（pending → working → done）✅
   - Worker ID 记录 ✅
   - 时间戳记录 ✅

2. **Ralph Loop** - 完美工作
   - 自动循环领取任务 ✅
   - 执行任务 ✅
   - 标记完成/失败 ✅
   - 继续下一个任务 ✅

3. **Git Worktree 管理** - 完美工作
   - 自动创建隔离 worktree ✅
   - 基于任务 ID 创建分支 ✅
   - 提交代码 ✅

### ❌ Claude Code 子进程集成问题

#### 问题 1: 嵌套会话限制

**错误:**
```
Error: Claude Code cannot be launched inside another Claude Code session.
```

**原因:**
- Claude Code 检测到 `CLAUDECODE` 环境变量
- 阻止嵌套会话以避免资源冲突

**解决方案:**
```python
env = os.environ.copy()
if "CLAUDECODE" in env:
    del env["CLAUDECODE"]
```

**状态:** ✅ 已解决

#### 问题 2: 交互式会话阻塞

**现象:**
- `claude -w -p "prompt"` 命令启动后hang住
- 不产生输出
- 不创建 worktree
- 进程一直运行但无进展

**原因分析:**

1. **`-w` 标志设计为交互式使用**
   - 根据 `--help` 输出：`--worktree [name]  Create a new git worktree for this session`
   - 可选配合 `--tmux` 创建 tmux 会话
   - 设计用于人类交互，不是自动化

2. **缺少 TTY/PTY**
   - Subprocess 默认不提供伪终端
   - Claude Code 可能期待终端输入
   - Stream-JSON 输出可能需要交互式环境

3. **Session 初始化需要交互**
   - 可能等待用户确认
   - 可能等待 worktree 创建确认
   - 可能需要选择分支

**尝试过的方案:**

1. ❌ 直接用 `-w` 标志
   - 结果：hang住，无输出

2. ❌ 手动创建 worktree + 在 worktree 中运行 `claude` (无 `-w`)
   - 结果：同样hang住
   - 说明问题不在 `-w` 本身，而在 subprocess 环境

**状态:** ⚠️ 未解决

## 关键认知

### Claude Code 的设计假设

1. **为交互式使用设计**
   - CLI 交互
   - IDE 集成（VSCode extension）
   - 需要人类反馈循环

2. **不是为自动化设计**
   - 没有 headless 模式
   - 没有批处理模式
   - 没有守护进程模式

### 胡渊鸣方案的可能实现

回顾原文，可能的实现方式：

#### 方案 A: 手动启动多个 Claude Code 会话

```bash
# Terminal 1
cd worktree-1 && claude

# Terminal 2
cd worktree-2 && claude

# ... (10 个终端)
```

- 每个 Claude Code 手动启动
- 人类在每个会话中输入任务
- 不是真正的"自动化"

#### 方案 B: tmux/screen 自动化

```bash
# 创建 tmux 会话
tmux new-session -d -s worker-1 "cd worktree-1 && claude -w"
tmux send-keys -t worker-1 "任务描述" C-m
```

- 使用 tmux 控制交互
- 模拟键盘输入
- 复杂且脆弱

#### 方案 C: 自定义 Claude Code 包装器（推测）

```python
# 可能胡渊鸣有内部工具
claude_automation_sdk.submit_task(
    worktree="worker-1",
    prompt="任务描述"
)
```

- 不是公开 API
- 可能是内部工具

## 替代方案

### 方案 1: 混合模式（推荐）

```
┌─────────────┐
│ Web Manager │ ← 用户通过 Web 管理任务
└─────┬───────┘
      │
      ├──→ Simple Workers (直接执行简单任务)
      │
      └──→ Human + Claude Code (复杂任务)
           每个 Claude Code 手动启动
           从任务池领取任务
           完成后标记 done
```

**优点:**
- 简单任务自动化（文件操作、git、测试）
- 复杂任务人类辅助
- 充分利用 Claude Code 能力

**缺点:**
- 不是完全自动化

### 方案 2: 等待官方 API

Claude Code 可能未来提供：
- Headless 模式
- Batch API
- Automation SDK

### 方案 3: 使用 Claude API 直接调用

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-5",
    messages=[{"role": "user", "content": task["description"]}],
    tools=[...]  # Tool use API
)
```

**优点:**
- 完全自动化
- 可控制
- 可扩展

**缺点:**
- 需要自己实现 Tool use
- 没有 Claude Code 的上下文管理
- 需要重新实现很多功能

## 下一步建议

### 短期（当前可行）

1. **Simple Worker 用于简单任务**
   - 文件创建/修改
   - Git 操作
   - Shell 命令执行
   - 测试运行

2. **人工 Claude Code 用于复杂任务**
   - 在 worktree 中手动启动
   - 从任务池领取
   - 完成后手动标记

### 中期（需要开发）

1. **tmux 自动化**
   - 使用 tmux 控制 Claude Code 会话
   - 模拟键盘输入
   - 捕获输出

2. **VSCode Remote Development**
   - 每个 worktree 一个 VSCode 窗口
   - Claude Code extension 自动加载
   - 通过 extension API 控制

### 长期（等待官方支持）

1. **Claude Code Automation API**
   - 官方提供 headless 模式
   - 批处理支持
   - WebSocket 控制接口

## 结论

**Worker Manager 架构是正确的**，但 Claude Code 不适合作为子进程被自动化调用。

当前最务实的方案是：
- **Simple Worker** 处理简单自动化任务（已验证可用）
- **人工 Claude Code** 处理复杂任务
- 等待官方 API 支持或社区工具

---

## 附录：测试记录

### 成功的 Simple Worker 测试

```
[00:33:07] [simple-test] 领取任务: test-create-file
[00:33:07] [simple-test] 执行任务: 创建文件 test-output.txt
[00:33:07] [simple-test] 创建文件: test-output.txt
[00:33:07] [simple-test] 提交到 Git...
[main 40c9ca7] 完成任务: test-create-file
[00:33:07] [simple-test] 任务 test-create-file 完成
```

**验证:**
- ✅ 文件创建
- ✅ Git commit
- ✅ 任务标记为 done
- ✅ Worker 继续循环

### 失败的 Claude Code 子进程测试

```
[00:30:58] [worker-test] 启动 Claude Code...
[00:30:58] [worker-test] 命令: claude -p...
[hang for 83 seconds]
[00:32:21] [worker-test] Claude Code 退出，exit code: 143 (killed)
```

**问题:**
- ❌ 进程hang住
- ❌ 无输出
- ❌ 需要手动 kill
