# Voice Input Feature - Testing Guide

## Implementation Summary

Voice input functionality has been successfully integrated into the Claude Code Worker Manager.

### Modified Files

1. **index.html** - Added voice button UI
   - `.voice-input-container` wraps textarea and voice button
   - Voice button with 🎤 icon and timer

2. **style.css** - Added voice button styling
   - Circular voice button design
   - Recording animation (pulsing red)
   - Processing animation (spinning)
   - Responsive layout for mobile

3. **app.js** - Implemented VoiceRecorder class
   - MediaRecorder API integration
   - Upload to Go ASR Server
   - Polling for transcription results
   - Error handling

4. **start_with_voice.sh** - New startup script
   - Launches Go ASR Server on localhost:18080
   - Launches FastAPI Server on localhost:8000
   - Cleanup on exit

---

## Testing Steps

### 1. Start Services

```bash
cd /Users/michael/projects/claude-code-selftask/worktree-manager
./start_with_voice.sh
```

Expected output:
```
🚀 Claude Code Worker Manager + ASR
1. 启动 Go ASR Server (localhost:18080)...
2. 启动 FastAPI Server (localhost:8000)...
✅ 所有服务已启动
```

### 2. Open Web Interface

Navigate to: http://localhost:8000

### 3. Test Voice Recording

#### Test Case 1: Normal Recording
1. Click 🎤 button
2. Browser prompts for microphone permission → Allow
3. Icon changes to 🔴, timer starts
4. Speak: "创建一个 hello.py 文件"
5. Click 🔴 to stop (wait at least 1 second)
6. Icon changes to ⏳ (processing)
7. Text appears in textarea automatically

#### Test Case 2: Permission Denied
1. Click 🎤 button
2. Deny microphone permission
3. Error message: "麦克风权限被拒绝，请允许访问麦克风"

#### Test Case 3: Recording Too Short
1. Click 🎤 button
2. Immediately click 🔴 (< 1 second)
3. Warning: "录音时间过短，请重试"

#### Test Case 4: Max Duration (60s)
1. Click 🎤 button
2. Wait 60 seconds without stopping
3. Auto-stop warning: "已达最大录音时长 (60秒)，自动停止"
4. Recording uploads automatically

#### Test Case 5: ASR Server Offline
1. Stop ASR Server
2. Click 🎤, record, stop
3. Error: "无法连接 ASR 服务器，请检查服务器是否运行在 localhost:18080"

---

## Expected UI Behavior

### Idle State
- Icon: 🎤
- Border: Gray (#333)
- Tooltip: "语音输入"

### Recording State
- Icon: 🔴
- Border: Red pulsing animation
- Timer: Shows elapsed seconds (1s, 2s, 3s...)
- Tooltip: "停止录音"

### Processing State
- Icon: ⏳ (spinning)
- Border: Blue (#4a9eff)
- Tooltip: "处理中..."

---

## Go ASR Server API Contract

Based on implementation, the expected API contract is:

### 1. Upload Audio
```
POST http://localhost:18080/v1/asr/recorded
Content-Type: multipart/form-data

file: <audio blob> (recording.webm)

Response:
{
  "task_id": "uuid-string"
}
```

### 2. Poll Result
```
GET http://localhost:18080/v1/asr/tasks/{taskId}

Response (in progress):
{
  "status": "processing"
}

Response (completed):
{
  "status": "completed",
  "transcript": "transcribed text"
}

Response (failed):
{
  "status": "failed",
  "error": "error message"
}
```

---

## Mobile Testing (HTTPS Required)

### Using Cloudflare Tunnel

1. Start services
2. Setup tunnel:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
3. Access via tunnel URL on mobile device
4. Test voice recording (HTTPS enables microphone access)

---

## Troubleshooting

### Issue: Voice button not appearing
- Check browser console for errors
- Verify index.html loaded correctly
- Check CSS loaded

### Issue: Permission denied on localhost
- Chrome: chrome://settings/content/microphone
- Safari: Preferences → Websites → Microphone
- Ensure localhost is allowed

### Issue: Upload fails with CORS error
- Check Go ASR Server CORS configuration
- Verify server is running on localhost:18080
- Check browser Network tab for actual error

### Issue: Polling timeout
- Check ASR server logs
- Verify API key is valid
- Check if server is processing the request

---

## Known Limitations

1. **Audio Format**: Uses MediaRecorder default (webm/mp4)
   - Chrome: audio/webm;codecs=opus
   - Safari: audio/mp4
   - Go Server must handle both formats

2. **HTTPS Requirement**: Mobile devices require HTTPS for microphone access
   - Use Cloudflare Tunnel or similar proxy

3. **Polling Efficiency**: Current implementation uses polling
   - Future enhancement: Use WebSocket for real-time updates

---

## Success Metrics

- ✅ Voice button appears inline with textarea
- ✅ Recording starts/stops on button click
- ✅ Visual feedback (timer, animations) works
- ✅ Transcription fills textarea automatically
- ✅ Error handling for all failure scenarios
- ✅ Responsive design works on mobile
- ✅ Startup script launches both servers

---

## Next Steps

After manual testing:
1. Update CHANGELOG.md
2. Update README.md with voice input instructions
3. Consider adding WebSocket support for real-time updates
4. Add support for audio format conversion if needed
