# Claude Code Worker Manager

基于胡渊鸣《我给 10 个 Claude Code 打工》的 Worker 管理系统，提供 Web 界面管理和监控多个 Claude Code Worker。

## 功能特性

- **任务管理**: 通过 Web 界面添加、查看、管理任务
- **语音输入**: 集成 ASR 语音识别，支持语音添加任务
- **实时监控**: WebSocket 实时推送日志和状态更新
- **多 Worker 支持**: 支持多个 Claude Code Worker 并行执行任务
- **PWA 支持**: 可安装为渐进式 Web 应用，支持离线访问
- **移动端优化**: 响应式设计，支持手机浏览器访问
- **Worktree 隔离**: 每个 Worker 使用独立的 Git Worktree

## 技术栈

- **后端**: FastAPI + WebSocket
- **前端**: 原生 JavaScript (无框架)
- **语音识别**: Go ASR Server + MediaRecorder API
- **Worker**: Claude Code 2.1.50+ (原生 Worktree 支持)
- **PWA**: Service Worker + Manifest

## 快速开始

### 1. 安装依赖

```bash
cd worktree-manager
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 2. 启动服务器

#### 标准启动（无语音功能）

```bash
./start.sh
```

或手动启动：

```bash
./venv/bin/python main.py
```

#### 启动带语音输入功能

```bash
./start_with_voice.sh
```

这将同时启动：
- FastAPI Server (localhost:8000)
- Go ASR Server (localhost:18080)

注意：需要确保 Go ASR Server 已正确配置（见下文"语音输入配置"）

### 3. 访问界面

- **本地访问**: http://localhost:8000
- **局域网访问**: http://YOUR_IP:8000
- **API 文档**: http://localhost:8000/docs

## 使用说明

### 添加任务

#### 方式 1: 文本输入

1. 在 Web 界面的"添加新任务"区域输入任务描述
2. 点击"添加任务"按钮
3. 任务会自动添加到队列，等待 Worker 认领

#### 方式 2: 语音输入

1. 点击输入框右侧的 🎤 按钮
2. 允许浏览器访问麦克风权限（首次使用）
3. 对着麦克风说出任务描述（例如："创建一个 hello.py 文件"）
4. 再次点击 🔴 按钮停止录音
5. 系统自动识别并填充到输入框
6. 点击"添加任务"按钮提交

语音输入限制：
- 最短录音时长: 1 秒
- 最长录音时长: 60 秒
- 识别超时: 30 秒

### 启动 Worker

```bash
# 启动单个测试 Worker
./venv/bin/python worker_manager.py

# 或启动多个 Worker（需要修改 worker_manager.py 中的配置）
```

### 查看日志

Web 界面的"实时日志"区域会显示：
- WebSocket 连接状态
- 任务状态变更
- Worker 执行日志

## API 端点

### 系统状态
```
GET /api/status
```

### 任务管理
```
GET /api/tasks          # 获取任务列表
POST /api/tasks         # 创建新任务
PUT /api/tasks/{id}     # 更新任务状态
DELETE /api/tasks/{id}  # 删除任务
```

### Worker 状态
```
GET /api/workers
```

### WebSocket
```
WS /ws                  # 实时日志和事件推送
```

## 移动端访问

### 通过局域网访问

1. 确保手机和电脑在同一局域网
2. 获取电脑 IP 地址：
   ```bash
   ipconfig getifaddr en0  # macOS
   # 或
   ip addr show           # Linux
   ```
3. 在手机浏览器打开: `http://YOUR_IP:8000`

### 通过 Cloudflare Tunnel（外网访问）

```bash
# 安装 cloudflared
brew install cloudflare/cloudflare/cloudflared

# 启动临时隧道
cloudflared tunnel --url http://localhost:8000
```

### 安装为 PWA

1. 在浏览器中访问应用
2. 点击浏览器的"添加到主屏幕"或"安装"
3. 可以像原生应用一样使用

## 语音输入配置

### 前提条件

1. Go ASR Server 已安装并配置
2. 已设置 `DASHSCOPE_API_KEY` 环境变量

### 配置步骤

编辑 `start_with_voice.sh` 中的路径：

```bash
ASR_SERVER_DIR="/path/to/audio-asr-suite/go/audio-asr-go"
```

### 浏览器兼容性

- Chrome/Edge: 支持 (推荐)
- Safari: 支持
- Firefox: 支持
- 移动端: 需要 HTTPS (使用 Cloudflare Tunnel)

### HTTPS 访问（移动端）

```bash
cloudflared tunnel --url http://localhost:8000
```

通过生成的 HTTPS URL 访问即可使用语音功能。

## 文件结构

```
worktree-manager/
├── main.py                   # FastAPI 服务器
├── worker_manager.py         # Worker 管理逻辑
├── requirements.txt          # Python 依赖
├── start.sh                 # 启动脚本（标准）
├── start_with_voice.sh      # 启动脚本（含语音）
├── test_server.sh           # 测试脚本
├── VOICE_INPUT_TEST.md      # 语音功能测试指南
└── static/                  # 静态文件
    ├── index.html           # 主页面
    ├── style.css            # 样式
    ├── app.js               # 前端逻辑（含 VoiceRecorder）
    ├── manifest.json        # PWA 配置
    └── service-worker.js    # Service Worker
```

## 开发说明

### 修改 Worker 数量

编辑 `worker_manager.py`:

```python
manager = WorkerManager(max_workers=5)  # 修改为需要的数量
```

### 自定义样式

编辑 `static/style.css`，主要变量在 `:root` 中定义：

```css
:root {
    --primary-color: #00d4aa;
    --bg-dark: #0a0a0a;
    --bg-card: #1a1a1a;
    /* ... */
}
```

## 故障排除

### 端口被占用

修改 `main.py` 中的端口：

```python
uvicorn.run(app, host="0.0.0.0", port=8080)  # 改为其他端口
```

### WebSocket 连接失败

检查防火墙设置，确保端口已开放。

### 任务无法执行

1. 检查 `data/dev-tasks.json` 是否存在
2. 确保 Worker 正在运行
3. 查看实时日志中的错误信息

### 语音输入无法使用

1. 检查 Go ASR Server 是否运行在 localhost:18080
2. 确认浏览器已授予麦克风权限
3. 移动端需要使用 HTTPS (Cloudflare Tunnel)
4. 查看浏览器控制台和实时日志中的错误信息

## 许可证

MIT License

## 参考

- [胡渊鸣 - 我给 10 个 Claude Code 打工](https://x.com/taichi_graphics/status/1892365028076593392)
- [Claude Code 官方文档](https://docs.anthropic.com/claude-code)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
