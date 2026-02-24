# 快速开始指南

## 1 分钟启动 Web 管理界面

### 步骤 1: 测试环境

```bash
cd /Users/michael/projects/claude-code-selftask/worktree-manager
./test_server.sh
```

预期输出：
```
=========================================
测试 Claude Code Worker Manager
=========================================

1. 检查静态文件...
   ✓ 所有静态文件存在
2. 检查 Python 依赖...
   ✓ 依赖已安装
3. 检查应用配置...
   ✓ FastAPI 应用加载成功
4. 检查数据目录...
   ✓ 任务文件存在

=========================================
所有检查通过！
=========================================
```

### 步骤 2: 启动服务器

```bash
./start.sh
```

启动成功后会看到：
```
=========================================
🚀 Claude Code Worktree Manager 启动中...
=========================================
📍 本地访问: http://localhost:8000
📁 静态文件: /path/to/static
📁 任务文件: /path/to/data/dev-tasks.json
📱 WebSocket: ws://localhost:8000/ws
=========================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 步骤 3: 访问界面

打开浏览器访问: **http://localhost:8000**

你会看到：
- 系统状态卡片（Claude 版本、Worker 数量、任务统计）
- 添加任务表单
- 任务列表（支持过滤）
- 实时日志（WebSocket 连接状态）

### 步骤 4: 添加测试任务

在"添加新任务"区域输入：
```
创建文件 hello-web.txt，内容为 "Hello from Web Interface!"
```

点击"添加任务"，你会看到：
- 任务列表更新（新任务出现在顶部）
- 实时日志显示："任务已添加: 创建文件 hello-web.txt..."
- 系统状态中的"待处理任务"数量增加

### 步骤 5: 启动 Worker（可选）

在新终端窗口：
```bash
cd /Users/michael/projects/claude-code-selftask/worktree-manager
./venv/bin/python worker_manager.py
```

Worker 会自动：
1. 从队列中认领任务
2. 创建 Git Worktree
3. 启动 Claude Code 执行任务
4. 标记任务为完成
5. 返回步骤 1（循环执行）

## 移动端访问

### 在同一局域网内

1. 获取电脑 IP：
   ```bash
   ipconfig getifaddr en0  # macOS
   ```

2. 在手机浏览器打开：
   ```
   http://YOUR_IP:8000
   ```

### 安装为 PWA

在手机浏览器：
1. 访问应用
2. 点击浏览器菜单
3. 选择"添加到主屏幕"或"安装"
4. 应用会像原生 App 一样出现在主屏幕

## 测试 API（可选）

```bash
./venv/bin/python demo_test.py
```

这会测试：
- GET /api/status
- GET /api/tasks
- POST /api/tasks
- 任务列表验证

## API 文档

访问 **http://localhost:8000/docs** 查看交互式 API 文档（Swagger UI）

## 故障排除

### 端口 8000 被占用

```bash
# 查找占用进程
lsof -i :8000

# 杀掉进程
kill -9 <PID>

# 或修改 main.py 中的端口
```

### WebSocket 无法连接

- 检查浏览器控制台（F12）是否有错误
- 确认服务器正在运行
- 检查防火墙设置

### 任务不执行

- 确保 Worker 正在运行（`./venv/bin/python worker_manager.py`）
- 检查 `data/dev-tasks.json` 文件权限
- 查看实时日志中的错误信息

## 下一步

- 添加更多任务测试系统
- 启动多个 Worker 进行并行测试
- 配置 Cloudflare Tunnel 实现外网访问
- 自定义样式和主题

## 文档

- **完整文档**: [README.md](README.md)
- **实施报告**: [IMPLEMENTATION.md](IMPLEMENTATION.md)
- **技术方案**: [SOLUTION.md](SOLUTION.md)

---

**享受自动化工作流！** 🚀
