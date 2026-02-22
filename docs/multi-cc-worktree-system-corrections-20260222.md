# 多 Claude Code 并行系统 - 调研修正

**日期:** 2026-02-22
**原因:** 与文章内容核对后发现的差异

---

## ❌ 错误 1: 任务池格式不应复用掌天瓶

**错误方案（之前）:**
```json
{
  "tasks": [{
    "id": "task-001",
    "agent": "backend-coder",  // ❌ 这是掌天瓶的概念
    "status": "pending"
  }]
}
```

**正确方案（文章）:**
```json
{
  "tasks": [
    {
      "id": "task-001",
      "description": "实现用户认证功能",
      "status": "pending"  // pending | working | done
    },
    {
      "id": "task-002",
      "description": "修复登录页面 bug",
      "status": "done"
    }
  ]
}
```

**原因:** 文章中是纯粹的任务队列，没有"代理"概念。每个 worker 只是认领任务干活，不区分 backend/frontend。

---

## ❌ 错误 2: CLAUDE.md 不应复用掌天瓶格式

**文章中的 CLAUDE.md（简化版）:**

```markdown
## 任务生命周期

1. **领取任务**: 原子操作，从 data/dev-tasks.json 获取任务
2. **创建工作区**: git worktree add -b task/xxx ../voice-notes-worktrees/task-xxx
3. **分支隔离**: 每个 worktree 里面是一个独立的 Claude Code
4. **提交代码**: git commit 在各分支
5. **Merge + 测试**:
   - git fetch origin && git merge origin/main
   - npm test
6. **自动合并到 main**:
   - git fetch origin main
   - git rebase origin/main task-xxx && git push origin main
7. **检记完成**: 更新 dev-tasks.json（必须在这里记录，否则下次还会领到这个任务）
8. **清理**: git worktree remove + 删除本地分支

**现在把你的经验教训流淌到 PROGRESS.md 里面，总结你做了什么问题，遇到了什么难度。**

**同样的问题不要犯两次！**
```

**关键点：**
- ✅ 严格按照文章的步骤顺序
- ✅ 强调"检记完成"（更新 dev-tasks.json）的重要性
- ✅ 强调 PROGRESS.md 记录经验（AI 长记性）
- ❌ 不要混入掌天瓶的 Pipeline/Swarm/Autopilot 概念

---

## ❌ 缺失功能 1: 语音输入（Step 8）

**文章内容:**
> 打字速度也是瓶颈，一是最键盘本身就很慢，二是很多时候不方便键盘。于是我给系统的每个输入框都加上了语音识别 API。

**实现方案:**

### 前端（Web Speech API）

```html
<!-- static/index.html -->
<div class="task-input">
  <textarea id="taskDesc" placeholder="任务描述..."></textarea>
  <button id="voiceBtn">🎤 语音输入</button>
</div>

<script>
const voiceBtn = document.getElementById('voiceBtn');
const taskDesc = document.getElementById('taskDesc');

if ('webkitSpeechRecognition' in window) {
  const recognition = new webkitSpeechRecognition();
  recognition.lang = 'zh-CN';
  recognition.continuous = false;

  voiceBtn.onclick = () => {
    recognition.start();
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    taskDesc.value = transcript;
  };
}
</script>
```

### 移动端支持

- ✅ **Android Chrome:** 完美支持 Web Speech API
- ⚠️ **iOS Safari:** 支持但需要用户手动触发

**或者使用云端语音识别（更稳定）:**
- Google Cloud Speech-to-Text
- Azure Speech Service
- 讯飞语音听写 API

---

## ❌ 缺失功能 2: Web 界面中的 Plan Mode（Step 9）

**文章内容:**
> Claude Code 的 Plan 模式是非常强大的，考虑到实际上没有人去 review AI 写的代码，Plan Mode 至少可以在开始干活之前让 AI 跟明确一下我的意图。

**实现方案:**

### 后端 API（main.py）

```python
@app.post("/workers/{worker_id}/start")
async def start_worker(
    worker_id: int,
    task_id: str,
    use_plan_mode: bool = False  # 新增参数
):
    """启动 Worker"""
    task = get_task(task_id)

    if use_plan_mode:
        # 先进入 Plan Mode
        await run_claude_code(
            worktree_path=f".worktrees/worker-{worker_id}",
            prompt=f"请制定计划：{task['description']}",
            permission_mode="plan"  # 使用 --permission-mode plan
        )
        # 用户批准后，再执行
        await run_claude_code(
            worktree_path=f".worktrees/worker-{worker_id}",
            prompt="执行计划",
            permission_mode="default"
        )
    else:
        # 直接干活
        await run_claude_code(
            worktree_path=f".worktrees/worker-{worker_id}",
            prompt=f"干活：{task['description']}，干完请退出 (exit)"
        )
```

### 前端界面

```html
<!-- static/index.html -->
<div class="task-card">
  <h3>Task: 实现用户认证</h3>
  <button onclick="startWorker(1, 'task-001', false)">直接执行</button>
  <button onclick="startWorker(1, 'task-001', true)">Plan Mode</button>
</div>
```

**Claude Code 的 Plan Mode 调用:**

```bash
# 进入 Plan Mode
claude -p "请制定计划：实现用户认证" \
  --permission-mode plan \
  --dangerously-skip-permissions

# 批准后执行
claude -p "执行计划" \
  --resume <session-id>
```

---

## ✅ 正确的地方

### 1. Git Worktree 架构
✅ **完全正确**，文章就是这么做的。

### 2. Python Subprocess 调度
✅ **完全正确**，文章使用：
```bash
claude -p [prompt] --dangerously-skip-permissions \
      --output-format stream-json --verbose
```

### 3. Ralph Loop
✅ **完全正确**，文章就是"干活→退出→外部重启"。

### 4. Web Manager
✅ **完全正确**，FastAPI + WebSocket 是合理选择。

### 5. 移动端 PWA
✅ **完全正确**，文章中就是用 Safari 添加到主屏幕（PWA）。

---

## ✅ 安卓支持确认

**文章中用的是 iPhone，但安卓支持更好：**

| 功能 | iOS | Android | 优势 |
|------|-----|---------|------|
| PWA 添加到主屏幕 | ✅ | ✅ | 安卓更简单 |
| 语音输入 | ⚠️ 需触发 | ✅ 完美 | 安卓 Chrome 原生支持 |
| 后台运行 | ❌ | ✅ | 安卓可后台保持连接 |
| 推送通知 | ⚠️ iOS 16.4+ | ✅ | 安卓无限制 |

**是的，就是移动 H5：**
- ✅ 响应式 Web 应用（HTML5）
- ✅ PWA 技术让它"像"原生 App
- ✅ 通过浏览器访问，无需安装

**访问方式（安卓）：**
1. **本地网络：** `http://192.168.x.x:8000`（同 WiFi）
2. **Tailscale：** 安装 Tailscale App，访问内网 IP
3. **Cloudflare Tunnel：** 公网域名访问

**添加到主屏幕（安卓 Chrome）：**
1. 打开 `http://192.168.x.x:8000`
2. 点击右上角菜单（三个点）
3. 选择"添加到主屏幕"
4. 确认，图标出现

---

## 📋 修正后的实施清单

### P0 - 必须实现（文章核心）

1. ✅ Git Worktree 管理
2. ✅ Claude Code 进程管理（subprocess + stream-json）
3. ✅ 简化的任务队列（`dev-tasks.json`，**不用掌天瓶格式**）
4. ✅ Ralph Loop（干活→退出→重启）
5. ✅ Web 界面（展示 worker 状态、任务列表、日志）
6. ✅ CLAUDE.md 定义"干活"逻辑（**严格按文章格式**）
7. ✅ PROGRESS.md 记录经验

### P1 - 文章提到的增强

1. ✅ 实时日志推送（WebSocket）
2. ✅ 语音输入（Web Speech API 或云端 API）
3. ✅ Plan Mode 触发（Web 界面按钮）
4. ✅ 移动端 PWA（安卓支持更好）

### P2 - 可选功能

1. ✅ Tailscale/Cloudflare Tunnel 远程访问
2. ✅ 多 worker 并行度配置
3. ✅ 统计和监控

---

## 总结

**核心问题：**
- ❌ 我之前试图"融合"掌天瓶，但文章的系统更简单纯粹
- ❌ 任务池不应有"agent"字段
- ❌ CLAUDE.md 应该纯粹按文章格式，不混入掌天瓶概念

**正确做法：**
- ✅ **完全按文章方式实现**，不要过度设计
- ✅ 任务池就是简单的 `{id, description, status}`
- ✅ Worker 不区分角色，都是通用的"干活"机器
- ✅ 添加语音输入和 Plan Mode 触发

**安卓支持：**
- ✅ **完全支持，且体验优于 iOS**
- ✅ 就是响应式 H5 + PWA
