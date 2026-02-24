// Real-time WebSocket Voice Recorder for Go ASR Server
// 协议: run-task → task-started → binary PCM → result-generated → finish-task → task-finished

class RealtimeVoiceRecorder {
    constructor(app) {
        this.app = app;
        this.ws = null;
        this.mediaStream = null;
        this.audioContext = null;
        this.processor = null;
        this.startTime = null;
        this.timerInterval = null;
        this.isRecording = false;
        this.taskReady = false;
        this.transcriptBuffer = '';
        this.taskId = 'voice-' + Date.now();

        this.WS_URL = 'ws://localhost:18080/api-ws/v1/inference';
        this.VOCABULARY_ID = 'vocab-mhot-136d447d097c4d28ab94cdf6f82092e3';
        this.MAX_DURATION = 60000;
    }

    async startRecording() {
        if (this.isRecording) return;

        try {
            // 1. 获取麦克风
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true }
            });

            // 2. 连接 WebSocket 并发送 run-task
            this.taskId = 'voice-' + Date.now();
            this.taskReady = false;
            this.transcriptBuffer = '';
            await this.connectAndInit();

            // 3. 创建音频管道
            // 浏览器通常只支持 44100/48000Hz，需要手动降采样到 16000Hz
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const nativeSampleRate = this.audioContext.sampleRate;
            this.app.log('浏览器采样率: ' + nativeSampleRate + 'Hz，目标: 16000Hz', 'info');

            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

            this.processor.onaudioprocess = (e) => {
                if (!this.isRecording || !this.taskReady || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
                const inputData = e.inputBuffer.getChannelData(0);
                // 从浏览器原生采样率降采样到 16000Hz
                const downsampled = this.downsample(inputData, nativeSampleRate, 16000);
                const pcm16 = this.floatTo16BitPCM(downsampled);
                this.ws.send(pcm16);
            };

            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

            this.isRecording = true;
            this.startTime = Date.now();
            this.updateUI('recording');
            this.startTimer();
            this.app.log('开始实时语音识别...', 'info');

            setTimeout(() => {
                if (this.isRecording) {
                    this.app.log('已达最大录音时长', 'warning');
                    this.stopRecording();
                }
            }, this.MAX_DURATION);

        } catch (error) {
            console.error('录音失败:', error);
            if (error.name === 'NotAllowedError') {
                this.app.log('麦克风权限被拒绝', 'error');
            } else {
                this.app.log('录音失败: ' + error.message, 'error');
            }
            this.cleanup();
        }
    }

    connectAndInit() {
        return new Promise((resolve, reject) => {
            this.app.log('连接 ASR 服务...', 'info');
            this.ws = new WebSocket(this.WS_URL);
            this.ws.binaryType = 'arraybuffer';

            const timeout = setTimeout(() => {
                if (this.ws.readyState === WebSocket.CONNECTING) {
                    this.ws.close();
                    reject(new Error('连接超时'));
                }
            }, 8000);

            this.ws.onopen = () => {
                clearTimeout(timeout);
                this.app.log('WebSocket 已连接，初始化识别任务...', 'info');

                // 发送 run-task 消息（FunASR DashScope 协议）
                this.ws.send(JSON.stringify({
                    header: {
                        action: 'run-task',
                        task_id: this.taskId,
                        streaming: 'duplex'
                    },
                    payload: {
                        task_group: 'audio',
                        task: 'asr',
                        function: 'recognition',
                        model: 'fun-asr-realtime',
                        parameters: {
                            format: 'pcm',
                            sample_rate: 16000,
                            vocabulary_id: this.VOCABULARY_ID
                        },
                        input: {}
                    }
                }));
            };

            this.ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    const headerEvent = msg.header && msg.header.event;

                    switch (headerEvent) {
                        case 'task-started':
                            this.taskReady = true;
                            this.app.log('识别任务已启动，请说话...', 'success');
                            resolve();
                            break;

                        case 'result-generated':
                            this.handleResult(msg);
                            break;

                        case 'task-finished':
                            this.handleFinished(msg);
                            break;

                        case 'task-failed':
                            const errMsg = (msg.payload && msg.payload.output && msg.payload.output.message) || '识别失败';
                            this.app.log('识别失败: ' + errMsg, 'error');
                            if (!this.taskReady) reject(new Error(errMsg));
                            break;

                        default:
                            console.log('ASR 消息:', msg);
                    }
                } catch (e) {
                    console.error('解析 ASR 消息失败:', e, event.data);
                }
            };

            this.ws.onerror = (err) => {
                clearTimeout(timeout);
                console.error('WebSocket 错误:', err);
                this.app.log('ASR WebSocket 连接失败，请确认 ASR 服务正在运行', 'error');
                reject(new Error('WebSocket 连接失败'));
            };

            this.ws.onclose = () => {
                this.taskReady = false;
            };
        });
    }

    handleResult(msg) {
        const sentence = msg.payload && msg.payload.output && msg.payload.output.sentence;
        if (!sentence) return;

        const text = sentence.text || '';
        const isFinal = sentence.sentence_end || false;

        if (text) {
            this.transcriptBuffer = text;

            // 实时更新到输入框
            const textarea = document.getElementById('task-description');
            if (textarea) textarea.value = text;

            if (isFinal) {
                this.app.log('识别: ' + text, 'success');
            }
        }
    }

    handleFinished(msg) {
        this.app.log('识别任务完成', 'info');
        this.fillResult();
    }

    stopRecording() {
        if (!this.isRecording) return;
        this.isRecording = false;
        this.stopTimer();
        this.updateUI('processing');
        this.app.log('停止录音，等待最终结果...', 'info');

        // 发送 finish-task
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                header: {
                    action: 'finish-task',
                    task_id: this.taskId
                },
                payload: { input: {} }
            }));

            // 超时保护：3秒后如果还没收到 task-finished，强制结束
            setTimeout(() => this.fillResult(), 3000);
        } else {
            this.fillResult();
        }
    }

    fillResult() {
        if (this._filled) return; // 防止重复
        this._filled = true;

        if (this.transcriptBuffer) {
            const textarea = document.getElementById('task-description');
            if (textarea) {
                textarea.value = this.transcriptBuffer;
                textarea.focus();
            }
            this.app.log('语音输入完成: ' + this.transcriptBuffer, 'success');
        } else {
            this.app.log('未识别到语音内容', 'warning');
        }

        this.cleanup();
    }

    cleanup() {
        if (this.processor) { this.processor.disconnect(); this.processor = null; }
        if (this.audioContext) { this.audioContext.close().catch(() => {}); this.audioContext = null; }
        if (this.mediaStream) { this.mediaStream.getTracks().forEach(t => t.stop()); this.mediaStream = null; }
        if (this.ws) { this.ws.close(); this.ws = null; }
        this.isRecording = false;
        this.taskReady = false;
        this._filled = false;
        this.updateUI('idle');
    }

    downsample(inputBuffer, inputRate, outputRate) {
        if (inputRate === outputRate) return inputBuffer;
        const ratio = inputRate / outputRate;
        const outputLength = Math.round(inputBuffer.length / ratio);
        const result = new Float32Array(outputLength);
        for (let i = 0; i < outputLength; i++) {
            const srcIndex = i * ratio;
            const low = Math.floor(srcIndex);
            const high = Math.min(low + 1, inputBuffer.length - 1);
            const frac = srcIndex - low;
            result[i] = inputBuffer[low] * (1 - frac) + inputBuffer[high] * frac;
        }
        return result;
    }

    floatTo16BitPCM(float32Array) {
        const buf = new ArrayBuffer(float32Array.length * 2);
        const view = new DataView(buf);
        for (let i = 0; i < float32Array.length; i++) {
            let s = Math.max(-1, Math.min(1, float32Array[i]));
            view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }
        return buf;
    }

    startTimer() {
        const el = document.querySelector('.voice-timer');
        if (!el) return;
        this.timerInterval = setInterval(() => {
            el.textContent = Math.floor((Date.now() - this.startTime) / 1000) + 's';
        }, 200);
    }

    stopTimer() {
        if (this.timerInterval) { clearInterval(this.timerInterval); this.timerInterval = null; }
    }

    updateUI(state) {
        const btn = document.getElementById('voice-btn');
        const icon = document.querySelector('.voice-icon');
        const timer = document.querySelector('.voice-timer');
        if (!btn || !icon || !timer) return;

        btn.classList.remove('recording', 'processing');
        switch (state) {
            case 'recording':
                btn.classList.add('recording');
                icon.textContent = '🔴';
                timer.style.display = 'block';
                btn.title = '点击停止';
                break;
            case 'processing':
                btn.classList.add('processing');
                icon.textContent = '⏳';
                timer.style.display = 'none';
                btn.title = '等待结果...';
                break;
            default:
                icon.textContent = '🎤';
                timer.style.display = 'none';
                timer.textContent = '0s';
                btn.title = '语音输入';
        }
    }
}
