# GOAL — 目标总纲（持续执行，不许停止）

> 状态跟踪文件。每完成一项打勾并更新日期；发现新任务追加到对应里程碑，**不删除未完成项**。

## 使命

打造一款**普惠全球的全设备同声传译软件**，基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)（Apache-2.0）开源引擎，
让任何人在游戏、小说、网页、会议、视频场景下都能零门槛跨语言沟通。

## 硬性需求（用户原始需求，全要）

- [x] 实时语音翻译字幕（麦克风 → ASR → 翻译 → 双语悬浮字幕）
- [ ] 屏幕文字 / OCR 翻译（游戏文本、小说、网页）
- [ ] 反向语音输出（TTS 朗读译文）
- [ ] 整篇阅读模式 + 结果可复制 / 导出
- [ ] 全平台（架构目标跨平台；Windows 先行，macOS/Linux 跟进）
- [x] **本地翻译为显性目标**：离线为主，API（`SIMUL_API_*`）仅可选
- [x] GitHub Actions 构建 + **tag 自动上传 Release**

## 技术决策（已定，见 DECISION.md）

组合式 Adopt：sherpa-onnx（ASR/VAD/TTS）+ Argos Translate（离线 NMT，英语枢纽 pivot）+ Tauri 2（壳）+ Python 管线子进程。

## 里程碑

### M6 — 安卓 / 移动端（2026-09-24 立项，用户确认跨平台诉求）
- [ ] spike：sherpa-onnx AAR 真机跑通 VAD+ASR（本机工具链已齐：adb/JDK17+21/gradle/Android SDK）
- [ ] NMT 移动端选型：Bergamot C++（首选，OPUS 同源）vs llama.cpp 小模型 vs API 过渡
- [ ] 壳选型：Tauri 2 Android vs 官方 sherpa-onnx Flutter 插件
- [ ] **区域截屏→OCR→中文** 移动端实现（MediaProjection + ONNX OCR，天然可跨）
- [ ] CI：GitHub Actions 出 APK 挂同一 Release

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
- [ ] 多音源选择 UI（麦克风 / 系统声音 / 指定应用）

#### M1 途中修复的坑（2026-09-24）
- [x] Argos 语对下载 403：argos-net.com 拒 Python 默认 UA → 浏览器 UA + 只走 https（ipfs 回落会无限挂起）
- [x] `ensure_pair` 死锁：持 `Lock` 内重入 `installed_pairs()` → 改 `RLock`（此前所有下载路径必卡死）

### M2 — 输出面补全
- [x] **TTS 朗读译文**（`tts_engine.py`，sherpa-onnx OfflineTts + Kokoro multi-lang v1.0，310MB/24kHz，en/zh/ja/es/fr/it/pt 七语种；2026-09-24 英中双句实测合成+播放通过，其余语种英文音色兜底）
- [ ] TTS 接入字幕管线（每条译文可选朗读）
- [x] **字幕历史面板 + 一键复制 / 导出 srt/txt**（emit 自动记录，退出 atexit 落盘 `subtitle_session.txt/.srt`，2026-09-24 实测）
- [ ] 整篇阅读模式（段落重排、可读性版式）

### M3 — 屏幕文字翻译
- [x] **OCR 抓屏翻译**（`demo_ocr.py`：RapidOCR 离线；全屏/区域/`--img` 图片三模式，2026-09-24 合成图 + 真实屏实测通过，复用 emit 字幕/历史/导出链路）
- [x] **阅读模式（整篇文档双语对照）**（`read_doc.py`：空行分段 + 长段句读打包，输出 `.bilingual.txt`，2026-09-24 实测）
- [ ] OCR 与字幕悬浮窗共存交互（Tauri 壳）

### M4 — 分发体验
- [ ] 安装包全量化：模型/管线随包分发或首启按需下载（当前 1.68MB 壳仅指向本机 `SIMUL_PYTHON`）
- [ ] 语对包管理界面（已装/未装/下载进度）

### M5 — 跨平台
- [ ] 三平台 CI 矩阵（Windows/macOS/Linux，tag → 同一 Release 挂三份包）
- [ ] macOS 本地验证
- [ ] Linux 本地验证
- [ ] 移动端 → 见 M6

## 每日推进规则

1. 完成项打勾 + 注明日期；进行中标 🔄；阻塞标 ⚠️ 并写明解除条件。
2. **不停机**：当前任务完成即刻进入下一项；阻塞项跳过，继续其他里程碑。
3. 每个可交付动作完成后 commit + push；对外可见的里程碑打 tag 出 Release。
