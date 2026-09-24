# 同声传译软件 — 预研决策记录（lyco OODA 第一轮）

> 需求（已确认一行版）：基于 sherpa-onnx 打造全设备通用同声传译软件——实时语音翻译字幕 + 屏幕文字/OCR 翻译 + 反向语音输出 + 阅读模式/导出；翻译离线为主、API 可选。

## 决策（Decide）

**组合式 Adopt**：不自研轮子，不绑死任何单一竞品。

| 层 | 选型 | 依据 |
|---|---|---|
| ASR/VAD/TTS 引擎 | **sherpa-onnx** (Apache-2.0, 14.9k★) | 用户指定；12 语言绑定、全平台+NPU、纯离线 |
| 离线文本翻译 NMT | **Argos Translate** (MIT, Bergamot系) | 验证通过：zh↔en 双向，pip 即装，完全离线 |
| 桌面壳/系统音频 | **Tauri 2 + Rust** | 克隆实证：TransEcho、my-translator 双双采用；`capture_windows.rs`/`resample`/`playback` 可参考（均 MIT） |
| 在线翻译（可选） | 用户自填 API Key | 普惠原则：默认免费离线，质量升级留给可选项 |

## 关键 niche 知识（调研实证）

1. **sherpa-onnx 没有 NMT 能力**——只有 ASR/TTS/VAD/降噪；"翻译环"必须外挂，全网项目各自拼装，这是产品化机会而非障碍。
2. Whisper 系语音翻译只支持 →英文单向；做"中→任意语"必须 **ASR + 文本NMT 分离式管线**（本项目采用）。
3. 系统声音抓取：Windows 用 **WASAPI loopback**，macOS 用 ScreenCaptureKit/BlackHole；mic-only 看不了视频打不了游戏。
4. 无竞品覆盖全需求：my-translator 的离线引擎仅限 Apple Silicon；**跨平台离线全场景同传是空白**——方向成立，非无人之境（各子赛道均有先例）。
5. sherpa-onnx 1.13.x Python API：入口为 `OnlineRecognizer.from_transducer`（旧 `from_streaming_zipformer` 已移除）；`stream.accept_waveform(sample_rate, waveform)` 需带采样率。
6. License 红线：RealTime-Screen-Translator 为 GPL-3.0，**代码不可复用**，只可借鉴思路；参考项目均 MIT 可克隆。

## 验证状态（Act / Re-observe）

- [x] **验证点 1（文件管线）**：wav → 流式ASR → Argos NMT → 双语字幕，端到端纯离线跑通（demo_file.py）
- [ ] **验证点 2（麦克风实时）**：demo_mic.py 运行中
- [ ] 验证点 3：系统声音捕获（WASAPI loopback）
- [ ] 验证点 4：悬浮字幕窗（Tauri 透明置顶窗）
- [ ] 验证点 5：TTS 朗读（sherpa-onnx offline TTS）

## 代码位置

- 最小 demo：`D:\Code\simul-demo\`（pipeline.py 原子管线 / demo_file.py / demo_mic.py）
- 参考克隆：`D:\Code\_research\`（TransEcho / my-translator / sherpa-onnx）

## 下一轮触发条件

验证点 2 通过 → 进入 OODA 第二轮：Rust 化管线 + Tauri 悬浮字幕壳（向产品化迈第一步）。
