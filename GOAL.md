# GOAL — 目标总纲（持续执行，不许停止）

> 状态跟踪文件。每完成一项打勾并更新日期；发现新任务追加到对应里程碑，**不删除未完成项**。

## 使命

打造一款**普惠全球的全设备同声传译软件**，基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)（Apache-2.0）开源引擎，
让任何人在游戏、小说、网页、会议、视频场景下都能零门槛跨语言沟通。

## 硬性需求（用户原始需求，全要）

- [x] 实时语音翻译字幕（麦克风 → ASR → 翻译 → 双语悬浮字幕）
- [x] 屏幕文字 / OCR 翻译（游戏文本、小说、网页）（2026-09-24：全屏/区域/拖拽圈选/图片四模式实测，默认出中文）
- [x] 反向语音输出（TTS 朗读译文）（2026-09-24：合成+播放实测，用户亲耳确认）
- [x] 整篇阅读模式 + 结果可复制 / 导出（2026-09-24：read_doc 双语对照 + txt/srt atexit 落盘）
- [ ] 🔄 全平台（架构目标跨平台；Windows 先行，macOS/Linux 跟进）——2026-09-24 三平台 CI 全绿（nsis/dmg/deb/AppImage 产物全出），本地验证与 M6 安卓待续
- [x] **本地翻译为显性目标**：离线为主，API（`SIMUL_API_*`）仅可选
- [x] GitHub Actions 构建 + **tag 自动上传 Release**

## 技术决策（已定，见 DECISION.md）

组合式 Adopt：sherpa-onnx（ASR/VAD/TTS）+ Argos Translate（离线 NMT，英语枢纽 pivot）+ Tauri 2（壳）+ Python 管线子进程。

## 里程碑

### M6 — 安卓 / 移动端（2026-09-24 立项，用户确认跨平台诉求）
- [ ] 🔄 spike：sherpa-onnx AAR 真机跑通 VAD+ASR（本机工具链已齐：adb/JDK17+21/gradle/Android SDK）——2026-09-24 工程骨架完成（`android/`：原生 Java + JitPack AAR v1.13.8 与桌面同版、中英双语流式 zipformer endpoint 断句、模型 assets 首启幂等拷贝、`fetch_model.py` 拉 75MB 模型），本地 `assembleDebug` 构建中；真机未连接（`adb devices` 空，待插手机开 USB 调试）
- [ ] NMT 移动端选型：Bergamot C++（首选，OPUS 同源）vs llama.cpp 小模型 vs API 过渡
- [ ] 壳选型：Tauri 2 Android vs 官方 sherpa-onnx Flutter 插件（spike 先原生 Java 直连 AAR 验证链路，壳选型后置）
- [ ] **区域截屏→OCR→中文** 移动端实现（MediaProjection + ONNX OCR，天然可跨）
- [x] CI：GitHub Actions 出 APK——2026-09-24 拍板**多 APK 按母语分渠道**：cn/en 双 flavor（id 后缀可并存 + `BuildConfig.DEFAULT_TARGET` 预留 NMT 目标语种）；**语对包离线可拷贝扩展**（外置目录扫描导入，NMT 落地时实现）；run 36003501308 全绿（android 3m7s 双 flavor + 三平台），坑：gradlew 缺执行位 exit 126 → git mode 100755 修复；**挂同一 Release 待 tag v0.2.0 实测**

### M0 — 原型闭环 ✅（2026-09-24）
- [x] 文件管线验证（wav → ASR → 离线NMT → 双语字幕，纯离线）
- [x] 视频端到端验证 + VAD 门控（8.9x 实时）+ 文本清洗
- [x] 翻译引擎层（语种检测 / pivot 路由 / 按需装包 / API 可选回落）
- [x] Tauri 悬浮字幕壳（透明置顶窗，读 Python 子进程 stdout）
- [x] CI：push 构建 artifact；**tag → 自动创建 Release 挂 NSIS 安装包**
- [x] CI：rust-cache（构建 5m → 2m23s）
- [x] CI 权限三坑修复（workflow permissions 块 / 仓库默认 write / rerun 不刷新权限快照）
- [x] Release v0.1.0 发布：https://github.com/lilyco-42/simul-overlay/releases/tag/v0.1.0

### M1 — 输入面扩展（进行中）
- [x] **22 个语对包安装完成 + pivot 路由实测**（2026-09-24：24 对装机；zh→ja/ko→zh/de→fr/ru→zh 两跳与 ar→en 直连全通过）
- [x] **WASAPI loopback 系统声音捕获**（`demo_system.py`，实测通过 2026-09-24：48k 立体声 loopback → 16k 单声道 → 全管线字幕输出）
- [ ] 麦克风实测（⚠️ Blocked：等用户检查系统麦克风权限后跑 `demo_mic.py 60`）
- [ ] 🔄 多音源选择 UI（麦克风 / 系统声音已进壳，指定应用待做）——2026-09-24 四合一控制条代码完成并过三平台 CI（run 36001487105 全绿：mac 1m38s / win 2m13s / linux 3m29s），待本地实跑验证

#### M1 途中修复的坑（2026-09-24）
- [x] Argos 语对下载 403：argos-net.com 拒 Python 默认 UA → 浏览器 UA + 只走 https（ipfs 回落会无限挂起）
- [x] `ensure_pair` 死锁：持 `Lock` 内重入 `installed_pairs()` → 改 `RLock`（此前所有下载路径必卡死）

### M2 — 输出面补全
- [x] **TTS 朗读译文**（`tts_engine.py`，sherpa-onnx OfflineTts + Kokoro multi-lang v1.0，310MB/24kHz，en/zh/ja/es/fr/it/pt 七语种；2026-09-24 英中双句实测合成+播放通过，其余语种英文音色兜底）
- [x] **TTS 接入字幕管线（每条译文可选朗读）**（2026-09-24：`SIMUL_TTS=1` emit 队列后台朗读实测，用户确认听到；壳内开关已接线）
- [x] **字幕历史面板 + 一键复制 / 导出 srt/txt**（emit 自动记录，退出 atexit 落盘 `subtitle_session.txt/.srt`，2026-09-24 实测）
- [x] **整篇阅读模式（段落重排、可读性版式）**（`read_doc.py`：空行分段 + 长段句读打包，2026-09-24 实测；stdout 流式推壳）

### M3 — 屏幕文字翻译
- [x] **OCR 抓屏翻译**（`demo_ocr.py`：RapidOCR 离线；全屏/区域/`--img` 图片三模式，2026-09-24 合成图 + 真实屏实测通过，复用 emit 字幕/历史/导出链路）
- [x] **阅读模式（整篇文档双语对照）**（`read_doc.py`：空行分段 + 长段句读打包，输出 `.bilingual.txt`，2026-09-24 实测）
- [ ] 🔄 OCR 与字幕悬浮窗共存交互（Tauri 壳）——2026-09-24 圈选OCR 按钮已进壳（`start_ocr`→`--select`），待实跑验证

### M4 — 分发体验（2026-09-24 用户拍板：**离线可用全量包**）
- [ ] 🔄 安装包全量化：模型/管线/核心语对**随包分发**（明确非首启下载）——路径：PyInstaller 打 Python 管线侧车 + 模型进 Tauri resources + CI 全量进 NSIS/dmg/deb，tag → Release 挂离线全量包（当前 1.68MB 壳仅指向本机 `SIMUL_PYTHON`，不满足）
  - 2026-09-24 定案：pipeline 写死路径已改三级解析（`SIMUL_MODEL_DIR` → frozen `_MEIPASS/models` → 仓库 `models/`）；Argos 语对靠 `ARGOS_PACKAGES_DIR` env 重定向随包目录；**首发核心 6 对 = zh↔en(166MB) + ja↔en(258MB) + ko↔en(258MB) ≈ 682MB**，其余语对留 `ensure_pair` 联网补装（全量 24 对 2.76GB 不随包）；PyInstaller 统一入口 `simul_pipe.py`（system/mic/ocr/read 子命令）已就位
  - 2026-09-24 进展：PyInstaller onedir **首打成功 403.6MB**（torch 109 + spacy 84 随 argos→stanza 链进包，实测翻译运行时真实加载 torch+stanza+spacy，暂不可 exclude）；runpy 动态 import 盲区已修（frozen 锚点，`demo_*` 顶层直跑不能 import 只锚纯模块）；**exe 实测通过**（frozen `read` + `ARGOS_PACKAGES_DIR` 随包六对 → en→ja 日文输出 rc=0）；`fetch_models.py`（ASR/VAD/TTS/argos 幂等拉取；VAD 挂 **asr-models** tag 非 vad-models）+ `requirements.txt` 就绪；核心 6 对已布局 `models/argos-packages`（682.1MB）；**Tauri 打包模式完成**（main.rs 运行时探测 resource_dir 下侧车 → 注入 `SIMUL_MODEL_DIR`/`ARGOS_PACKAGES_DIR`，无侧车回退开发模式，cargo check 绿；tauri.conf `resources/*` + `build_sidecar.py` 跨平台脚本 + CI Windows job 五步 `with_sidecar` 开关——torch 须先 CPU index 防 CUDA 膨胀）；待办：CI 全链验证 → tag v0.2.0（Windows NSIS 全量首发，mac/linux 轻包后补全量）
- [ ] 语对包管理界面（已装/未装/下载进度）

### M5 — 跨平台
- [x] **三平台 CI 矩阵**（Windows/macOS/Linux，tag → 同一 Release 挂三份包）——2026-09-24 run 35999279633 全绿：nsis 2m06s / dmg 3m57s / deb+AppImage 4m39s，artifact 全挂；坑：`bundle.targets:["nsis"]` 在 mac/Linux 被静默跳过 → 改 `--bundles` 按平台指定
- [ ] 🔄 macOS 产物验证——2026-09-24 artifact 真实下载校验通过（dmg 2.4MB，未过期），待目标系统实际安装运行
- [ ] 🔄 Linux 产物验证——2026-09-24 artifact 真实下载校验通过（deb+AppImage 179MB，未过期），待目标系统实际安装运行
- [ ] 移动端 → 见 M6

## 每日推进规则

1. 完成项打勾 + 注明日期；进行中标 🔄；阻塞标 ⚠️ 并写明解除条件。
2. **不停机**：当前任务完成即刻进入下一项；阻塞项跳过，继续其他里程碑。
3. 每个可交付动作完成后 commit + push；对外可见的里程碑打 tag 出 Release。
