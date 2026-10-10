# simul-overlay · 普惠同声传译（原型）

全离线、免费、跨平台为目标的同声传译软件原型。当前阶段：**Windows 悬浮字幕壳 + Python 管线**。

## 架构

```
麦克风/系统音频 → Silero VAD(门控) → sherpa-onnx 流式ASR → Argos 离线NMT → 双语字幕
                                                                          ├─ 控制台 (demo)
                                                                          └─ Tauri 悬浮窗 (app/)
```

- **ASR/TTS/VAD**: [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) (Apache-2.0)
- **离线翻译**: Argos Translate (MIT)，zh↔en 双向，可扩展语种
- **悬浮字幕壳**: Tauri 2 (Rust)，透明置顶窗，读取管线 stdout 流式渲染

## 快速开始（本地）

```bash
# 1. Python 环境
python -m venv .venv
.venv/Scripts/pip install sherpa-onnx argostranslate sounddevice soundfile numpy

# 2. 模型（见 DECISION.md 中链接；ASR 模型约 487MB + silero_vad.onnx）
#    解压到 models/ 下

# 3. 跑管线
.venv/Scripts/python demo_file.py models/your-audio.wav   # 文件模式
.venv/Scripts/python demo_mic.py 60                       # 麦克风模式

# 4. 悬浮字幕壳
cd app/src-tauri && cargo run
# 可选环境变量: SIMUL_PYTHON / SIMUL_DEMO 覆盖默认管线路径
```

## CI 构建

推送即触发 GitHub Actions（`build-windows.yml`）：Windows runner 编译 Tauri + 打 NSIS 安装包，
产物在 workflow artifact `windows-nsis-installer` 下载。

## 目录

- `pipeline.py` — 管线核心（VAD 分段器 / ASR / NMT / 字幕产出）
- `demo_file.py` / `demo_mic.py` — 文件 / 麦克风演示入口
- `app/` — Tauri 悬浮字幕壳
- `DECISION.md` — lyco 预研决策记录（候选对比、niche 知识、验证清单）
