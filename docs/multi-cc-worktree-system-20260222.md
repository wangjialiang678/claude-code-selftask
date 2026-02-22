# 多 Claude Code 并行系统调研报告

**调研日期:** 2026-02-22
**来源:** 胡渊鸣《我给 10 个 Claude Code 打工》
**目标:** 复刻多 CC 实例并行系统，支持移动端驱动

---

## 核心架构对比

### 掌天瓶（当前项目）vs 胡渊鸣系统

| 维度 | 掌天瓶 | 胡渊鸣系统 |
|------|--------|-----------|
| **并行方式** | 单 CC + 子代理（逻辑并行） | 多 CC 进程 + Git worktree（物理并行） |
| **任务分发** | Hook 驱动流水线/任务池 | dev-tasks.json + 文件锁 |
| **管理方式** | CLI 触发 | Web Manager 图形界面 |
| **持续运行** | Stop Hook 阻止退出 | Ralph loop（干活→退出→重启） |
| **远程访问** | 不支持 | SSH + Web Manager |

**融合方案:** 复用掌天瓶的任务池概念，改造成多实例物理并行。

---

## 技术栈选择

### 1. Git Worktree 并行架构

```
项目根目录/
├─ .worktrees/               # 工作区目录（gitignored）
│   ├─ worker-1/ (port 5200) # 独立的 git worktree
│   ├─ worker-2/ (port 5201)
│   └─ worker-N/
│
├─ data/                     # 共享数据（各 worktree symlink）
│   ├─ dev-tasks.json       # 任务队列
│   ├─ dev-task.lock.d/     # mkdir 原子锁
│   └─ .env                 # API keys
│
├─ CLAUDE.md                 # "干活"逻辑定义
└─ PROGRESS.md              # 进度追踪（主仓库）
```

**关键点:**
- 每个 worktree 独立 git 分支（`task/xxx`）
- 通过 symlink 共享 `dev-tasks.json`、API key
- ⚠️ **禁止 symlink PROGRESS.md**（需用 `git -C` 编辑主仓文件）

**复用掌天瓶资产:**
- ✅ `.claude/agentflow/scripts/claim-task.sh`（任务认领）
- ✅ `.claude/agentflow/scripts/complete-task.sh`（任务完成）
- ✅ `.claude/agentflow/scripts/lib/file-lock.sh`（mkdir 原子锁）

---

### 2. 任务队列和分发机制

**任务池格式** (复用掌天瓶的 `task-pool.json`):

```json
{
  "tasks": [
    {
      "id": "task-001",
      "description": "实现用户认证",
      "status": "pending",  // pending | claimed | completed
      "claimed_by": null,
      "claimed_at": null,
      "agent": "backend-coder"
    }
  ]
}
```

**领取流程** (原子操作):

```bash
# 1. 获取文件锁（mkdir 原子操作）
mkdir data/dev-task.lock.d/$$

# 2. 读取任务池，找到第一个 pending 任务
task_id=$(jq '.tasks[] | select(.status == "pending") | .id' | head -1)

# 3. 原子更新状态为 claimed
jq '.tasks |= map(if .id == $id then .status = "claimed" else . end)' \
   data/dev-tasks.json > data/dev-tasks.json.tmp
mv data/dev-tasks.json.tmp data/dev-tasks.json

# 4. 释放文件锁
rmdir data/dev-task.lock.d/$$

# 5. 返回任务详情
echo "$task_id"
```

---

### 3. Web 管理界面技术栈

**选择: FastAPI + WebSocket**

**理由:**
- ✅ 原生异步支持（20k+ req/s vs Flask 4k req/s）
- ✅ 内置 WebSocket（实时日志推送）
- ✅ 自动 API 文档（Swagger UI）
- ✅ 类型检查（Pydantic）

**核心功能:**

| 功能 | API 端点 | 说明 |
|------|---------|------|
| 启动 Worker | `POST /workers/{id}/start` | 创建 worktree + 启动 CC |
| 停止 Worker | `POST /workers/{id}/stop` | 终止 CC 进程 |
| 实时日志 | `WS /workers/{id}/logs` | 推送 stream-json 输出 |
| 任务列表 | `GET /tasks` | 读取 `dev-tasks.json` |
| 添加任务 | `POST /tasks` | 写入新任务 |

**Claude Code 调用方式:**

```python
import asyncio
import subprocess

async def run_claude_code(worktree_path, prompt, stream_callback):
    proc = await asyncio.create_subprocess_exec(
        'claude', '-p', prompt,
        '--dangerously-skip-permissions',
        '--output-format', 'stream-json',
        '--verbose',
        cwd=worktree_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    async for line in proc.stdout:
        data = json.loads(line)
        await stream_callback(data)  # 推送到 WebSocket

    return await proc.wait()
```

**Sources:**
- [FastAPI vs Flask 2025: Performance Comparison](https://strapi.io/blog/fastapi-vs-flask-python-framework-comparison)
- [Flask vs FastAPI: In-Depth Framework Comparison](https://betterstack.com/community/guides/scaling-python/flask-vs-fastapi/)

---

### 4. Ralph Loop 自动循环实现

**核心思想:** CC 完成任务后主动退出，外部 Manager 检测退出后重启。

**流程:**

```python
async def ralph_loop(worker_id: int, worktree_path: str):
    """Worker 主循环"""
    while True:
        # 1. 领任务（调用掌天瓶的 claim-task.sh）
        task = await claim_task(worker_id)
        if not task:
            logger.info(f"Worker {worker_id}: 无任务，休眠")
            await asyncio.sleep(10)
            continue

        # 2. 启动 Claude Code
        logger.info(f"Worker {worker_id}: 开始任务 {task['id']}")
        exit_code = await run_claude_code(
            worktree_path=worktree_path,
            prompt="干活，干完请退出 (exit)",
            stream_callback=lambda data: broadcast_log(worker_id, data)
        )

        # 3. 检查结果
        if exit_code == 0 and task_completed(task):
            await complete_task(task['id'])
            logger.info(f"Worker {worker_id}: 任务 {task['id']} 完成")
        else:
            await release_task(task['id'])
            logger.warning(f"Worker {worker_id}: 任务 {task['id']} 失败")
```

**CLAUDE.md 配置:**

```markdown
## 任务生命周期

1. **领取任务**: 从 `data/dev-tasks.json` 原子读取
2. **创建工作区**: `git worktree add -b task/xxx`
3. **提交代码**: `git commit` 在当前分支
4. **Merge + 测试**:
   - `git fetch origin && git merge origin/main`
   - `npm test`
5. **自动合并到 main**:
   - `git fetch origin main`
   - `git rebase origin/main && git push origin main`
6. **检记完成**: 更新 `dev-tasks.json`
7. **清理**: `git worktree remove + 删除本地分支`

**干完请退出 (exit)**
```

---

### 5. 移动端访问方案

**PWA (Progressive Web App) 支持:**

**必需组件:**

1. **manifest.json** (PWA 配置):

```json
{
  "name": "Claude Code Manager",
  "short_name": "CC Manager",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#000000",
  "icons": [
    {
      "src": "/static/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

2. **Service Worker** (离线支持):

```javascript
// sw.js
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open('cc-manager-v1').then(cache => {
      return cache.addAll([
        '/',
        '/static/app.js',
        '/static/styles.css'
      ]);
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
```

3. **HTML meta tags**:

```html
<link rel="manifest" href="/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
<link rel="apple-touch-icon" href="/static/icon-180.png">
```

**iOS Safari "添加到主屏幕" 步骤:**
1. 打开 Safari 访问 `http://192.168.x.x:8000`
2. 点击底部 "分享" 按钮
3. 选择 "添加到主屏幕"
4. 确认，图标出现在主屏幕

**Sources:**
- [PWA on iOS - Current Status & Limitations [2025]](https://brainhub.eu/library/pwa-on-ios)
- [Do Progressive Web Apps Work on iOS? Complete Guide for 2026](https://www.mobiloud.com/blog/progressive-web-apps-ios)

---

**网络访问方案:**

| 方案 | 适用场景 | 配置 | 优点 | 缺点 |
|------|---------|------|------|------|
| **局域网 IP** | 同一 WiFi | 零配置 | 简单快速 | 需要同网络 |
| **Tailscale** | 多设备私密访问 | 安装客户端 | 安全、P2P、免费 | 需要安装客户端 |
| **Cloudflare Tunnel** | 公网访问 | `cloudflared` | 免费、稳定、无需公网 IP | 需要注册账号 |
| **ngrok** | 临时分享 | 单命令启动 | 极简 | 免费版 URL 随机 |

**推荐组合:**
- **日常使用:** 局域网 IP (`http://192.168.1.100:8000`)
- **远程访问:** Tailscale (安全) 或 Cloudflare Tunnel (无需客户端)

**Tailscale 配置示例:**

```bash
# 1. 安装 Tailscale
brew install tailscale

# 2. 启动并登录
sudo tailscaled
tailscale up

# 3. 获取 Tailscale IP
tailscale ip

# 4. 在手机上安装 Tailscale App，用相同账号登录
# 5. 访问 http://<tailscale-ip>:8000
```

**Sources:**
- [ngrok Alternatives: Five Leading Tunneling Solutions](https://tailscale.com/learn/ngrok-alternatives)
- [Ngrok vs Cloudflare Tunnel vs Tailscale: Complete 2025-26](https://instatunnel.my/blog/comparing-the-big-three-a-comprehensive-analysis-of-ngrok-cloudflare-tunnel-and-tailscale-for-modern-development-teams)

---

### 6. 本地部署方案（不用 EC2）

**系统架构:**

```
项目根目录/
├─ worktree-manager/          # FastAPI 管理服务
│   ├─ main.py               # FastAPI 主服务 (port 8000)
│   ├─ worker_manager.py     # Worker 生命周期管理
│   ├─ cc_subprocess.py      # Claude Code 进程封装
│   ├─ models.py             # Pydantic 数据模型
│   ├─ static/               # 前端资源
│   │   ├─ index.html        # PWA 主页
│   │   ├─ manifest.json     # PWA 配置
│   │   ├─ sw.js            # Service Worker
│   │   ├─ app.js           # 前端逻辑 (WebSocket)
│   │   └─ styles.css
│   ├─ templates/            # Jinja2 模板
│   └─ requirements.txt      # 依赖列表
│
├─ .worktrees/               # Git worktree 工作区（gitignored）
│   ├─ worker-1/             # Worker 1 (port 5200)
│   ├─ worker-2/             # Worker 2 (port 5201)
│   └─ worker-N/
│
├─ data/                     # 共享数据
│   ├─ dev-tasks.json       # 任务队列
│   ├─ dev-task.lock.d/     # 文件锁目录
│   └─ .env                 # 环境变量
│
├─ .claude/                  # 掌天瓶配置（复用）
│   ├─ agents/               # 7 个代理定义
│   ├─ agentflow/
│   │   ├─ scripts/          # 任务池脚本（复用）
│   │   │   ├─ claim-task.sh
│   │   │   ├─ complete-task.sh
│   │   │   └─ lib/file-lock.sh
│   │   └─ agents.md
│   └─ settings.json
│
├─ CLAUDE.md                 # "干活"逻辑定义
└─ PROGRESS.md              # 进度追踪（主仓库）
```

**核心组件职责:**

| 组件 | 职责 | 技术栈 |
|------|------|--------|
| **FastAPI Server** | HTTP API + WebSocket 服务 | Python 3.11+, FastAPI, Uvicorn |
| **Worker Manager** | 创建/销毁 worktree，启动/停止 CC | subprocess, GitPython |
| **CC Subprocess** | 包装 `claude -p` 调用 | asyncio, subprocess |
| **Frontend** | PWA 界面，实时日志展示 | Vanilla JS, WebSocket |
| **Task Queue** | 复用掌天瓶的 `task-pool.json` | jq, file lock (复用) |

**启动流程:**

```bash
# 1. 安装依赖
cd worktree-manager
pip install -r requirements.txt

# 2. 启动 Manager
python main.py
# 或使用 Uvicorn 手动启动
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. 访问 Web 界面
# 本地浏览器：http://localhost:8000
# 移动端（同 WiFi）：http://192.168.x.x:8000
# 远程（Tailscale）：http://<tailscale-ip>:8000
```

**与 EC2 方案对比:**

| 维度 | 本地部署 | EC2 部署 |
|------|---------|----------|
| **成本** | ✅ 零成本（使用本地机器） | ⚠️ 按小时计费 |
| **延迟** | ✅ 本地运行，低延迟 | ⚠️ 网络延迟 |
| **数据隐私** | ✅ 数据不上云 | ⚠️ 云端存储 |
| **持续运行** | ⚠️ 需要本地机器开机 | ✅ 7x24 运行 |
| **远程访问** | ⚠️ 需要配置 Tailscale/Tunnel | ✅ 公网 IP 直接访问 |
| **资源限制** | ⚠️ 受本地机器性能限制 | ✅ 可弹性扩展 |

**推荐:**
- **日常开发:** 本地部署（成本低、隐私好）
- **生产环境/团队协作:** EC2 部署（高可用）

---

## 实施优先级

### P0 - 核心功能（MVP）

1. **Git Worktree 管理**
   - `create_worktree(worker_id, task)` - 创建工作区
   - `destroy_worktree(worker_id)` - 清理工作区
   - Symlink 共享数据（`dev-tasks.json`, `.env`）

2. **Claude Code 进程管理**
   - 启动 CC: `claude -p --output-format stream-json`
   - 读取 stream-json 输出
   - 监控进程状态（运行中/已退出）

3. **任务队列（复用掌天瓶）**
   - 复用 `.claude/agentflow/scripts/claim-task.sh`
   - 复用 `.claude/agentflow/scripts/complete-task.sh`
   - 复用 `.claude/agentflow/scripts/lib/file-lock.sh`

4. **FastAPI 基础服务**
   - `GET /workers` - 列出所有 worker 状态
   - `POST /workers/{id}/start` - 启动 worker
   - `POST /workers/{id}/stop` - 停止 worker
   - `GET /tasks` - 任务列表

5. **简单 Web 界面**
   - 显示 Worker 列表和状态
   - 显示任务队列
   - 手动启动/停止 Worker

### P1 - 自动化增强

1. **Ralph Loop**
   - Worker 主循环：领任务 → 启动 CC → 等待退出 → 检查结果
   - 自动重启机制
   - 错误处理和重试

2. **实时日志推送**
   - WebSocket 连接
   - Stream-json 解析
   - 前端日志展示（实时滚动）

3. **PROGRESS.md 集成**
   - 读取进度信息
   - 在 Web 界面展示

### P2 - 移动端支持

1. **PWA 配置**
   - `manifest.json`
   - Service Worker (`sw.js`)
   - Apple touch icon

2. **响应式设计**
   - 移动端适配
   - 触摸友好的 UI

3. **网络访问**
   - Tailscale 配置文档
   - Cloudflare Tunnel 配置文档

### P3 - 高级功能

1. **并行度配置**
   - 动态调整 worker 数量
   - 资源监控（CPU/内存）

2. **任务优先级**
   - 高优先级任务优先处理
   - 任务依赖关系

3. **统计和监控**
   - 任务完成率
   - Worker 利用率
   - 平均耗时

---

## 技术风险和挑战

### 1. Git Worktree 冲突管理

**风险:** 多个 worker 同时修改同一文件导致冲突。

**缓解方案:**
- 任务划分时避免文件重叠（前端/后端分离）
- Rebase 失败时自动回滚，重新认领任务
- PROGRESS.md 使用 `git -C` 编辑主仓库文件，避免 symlink

### 2. Claude Code 进程管理

**风险:** CC 进程僵死、内存泄漏、无限循环。

**缓解方案:**
- 设置超时时间（如 30 分钟）
- 监控进程资源占用
- 提供手动 kill 功能

### 3. 任务队列并发安全

**风险:** 多个 worker 同时读写 `dev-tasks.json` 导致数据损坏。

**缓解方案:**
- ✅ 已有 `mkdir` 原子锁（掌天瓶的 file-lock.sh）
- ✅ macOS/Linux 兼容（不依赖 `flock`）

### 4. 移动端兼容性

**风险:** iOS Safari 的 PWA 限制（50MB 缓存、后台限制）。

**缓解方案:**
- 最小化缓存资源
- 使用 WebSocket 长连接（不依赖后台刷新）
- 提供"唤醒"机制（用户手动刷新）

---

## 下一步行动

### 立即行动

1. **进入 PLAN 模式**
   - 创建实施计划（`plans/multi-cc-worktree-system.md`）
   - 拆分任务清单（P0 → P1 → P2 → P3）

2. **确认技术选型**
   - Python 3.11+ ✅
   - FastAPI + Uvicorn ✅
   - Vanilla JS (无框架) ✅

3. **复用掌天瓶资产**
   - 任务池脚本 (`.claude/agentflow/scripts/`) ✅
   - 文件锁机制 (`lib/file-lock.sh`) ✅
   - 代理定义 (`.claude/agents/`) ✅

### 待用户确认

1. **部署方式**
   - 本地运行（推荐）？
   - 远程访问方案（Tailscale vs Cloudflare Tunnel）？

2. **Worker 数量**
   - 建议从 3 个 worker 开始
   - 后续根据机器性能调整

3. **UI 风格**
   - 终端风格（黑底绿字）？
   - 现代风格（Material Design）？
   - 还是复刻文章中的界面？

---

## 总结

**核心发现:**

1. ✅ **掌天瓶有大量可复用资产** - 任务池、文件锁、代理定义
2. ✅ **技术栈成熟** - FastAPI、Git worktree、PWA 均有完善生态
3. ✅ **本地部署可行** - 无需 EC2，通过 Tailscale/Tunnel 实现移动端访问
4. ⚠️ **需要改造思路** - 从"阻止退出"改为"主动退出后重启"

**与原文差异:**

| 维度 | 原文（胡渊鸣） | 本方案 |
|------|--------------|--------|
| 部署环境 | EC2 服务器 | 本地机器 |
| 远程访问 | SSH + 公网 IP | Tailscale/Cloudflare Tunnel |
| 任务队列 | 自己实现 | 复用掌天瓶的 `task-pool.json` |
| 代理角色 | 未提及 | 复用掌天瓶的 7 个代理 |

**预期效果:**

- 🚀 **10 倍吞吐量提升** - 5 个 worker 并行处理任务
- 📱 **移动端随时驱动** - PWA + Tailscale，iPhone 上一键操作
- 💰 **零额外成本** - 本地运行，无需云服务器
- 🔄 **无缝融合** - 与掌天瓶现有架构兼容

---

**调研完成。是否进入规划阶段？**
