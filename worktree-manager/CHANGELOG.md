# Changelog - Claude Code Worker Manager

All notable changes to this project will be documented in this file.

---

## [v1.1.0] - 2026-02-23

### Added

- **Voice Input Feature** - 集成 ASR 语音识别功能
  - MediaRecorder API 录音功能
  - 实时录音状态显示（录音中、处理中）
  - 录音时长限制（最小 1 秒，最大 60 秒）
  - Go ASR Server 集成（localhost:18080）
  - 自动轮询识别结果（30 秒超时）
  - 识别完成后自动填充任务输入框
  - 完整错误处理（权限拒绝、上传失败、识别超时）

- **UI Enhancements**
  - 语音输入按钮（🎤 图标）
  - 录音状态动画（红色脉冲效果）
  - 处理状态动画（旋转加载效果）
  - 录音时长计时器
  - 响应式设计适配移动端

- **Documentation**
  - `VOICE_INPUT_TEST.md` - 语音功能测试指南
  - README.md 更新语音输入使用说明
  - 语音输入配置说明

- **Startup Script**
  - `start_with_voice.sh` - 同时启动 FastAPI + Go ASR Server
  - 优雅的服务启停管理
  - PID 文件追踪
  - 信号处理和清理

### Changed

- **index.html**
  - 添加 `.voice-input-container` 布局
  - 添加语音按钮和计时器元素

- **style.css**
  - 新增语音按钮样式
  - 录音/处理状态动画
  - 移动端响应式优化

- **app.js**
  - 新增 `VoiceRecorder` 类
  - 集成 MediaRecorder API
  - 实现上传和轮询逻辑
  - WorkerManagerApp 集成语音录制器

### Technical Details

- **Audio Format**: MediaRecorder 默认格式（Chrome: audio/webm, Safari: audio/mp4）
- **ASR Server**: Go ASR Server 运行在 localhost:18080
- **Polling**: 每 500ms 轮询一次，30s 超时
- **Duration Limits**: 1s - 60s
- **HTTPS**: 移动端需要 HTTPS（通过 Cloudflare Tunnel）

---

## [v1.0.0] - 2026-02-23

### Initial Release

- FastAPI + WebSocket 后端
- 原生 JavaScript 前端
- Claude Code Worker 管理
- 实时日志推送
- PWA 支持
- 响应式设计
- Git Worktree 隔离
